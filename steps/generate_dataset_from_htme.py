import ast
import base64
import concurrent.futures
import itertools
import logging
import os
import re
import time
import zlib
from datetime import datetime
from itertools import groupby

import boto3
import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql import SparkSession

from steps.logger import setup_logging

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def main(spark, s3_client, s3_htme_bucket,
         s3_prefix, secrets_collections, keys_map,
         run_time_stamp, s3_publish_bucket, published_database_name):
    keys = get_list_keys_for_prefix(s3_client, s3_htme_bucket, s3_prefix)
    list_of_dicts = group_keys_by_collection(keys)
    list_of_dicts_filtered = get_collections_in_secrets(list_of_dicts, secrets_collections)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        _ = executor.map(consolidate_rdd_per_collection, list_of_dicts_filtered,
                         itertools.repeat(secrets_collections),
                         itertools.repeat(s3_htme_bucket),
                         itertools.repeat(spark),
                         itertools.repeat(keys_map),
                         itertools.repeat(run_time_stamp),
                         itertools.repeat(s3_publish_bucket),
                         itertools.repeat(published_database_name))


def get_collections_in_secrets(list_of_dicts, secrets_collections):
    filtered_list = []
    for collection_dict in list_of_dicts:
        for collection_name, collection_files_keys in collection_dict.items():
            if collection_name.lower() in secrets_collections:
                filtered_list.append(collection_dict)
            else:
                logging.error("%s is not present in the collections list" % collection_name)
    return filtered_list


def get_client(service_name):
    client = boto3.client(service_name)
    return client


def get_list_keys_for_prefix(s3_client, s3_htme_bucket, s3_prefix):
    keys = []
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=s3_htme_bucket, Prefix=s3_prefix)
    for page in pages:
        for obj in page['Contents']:
            keys.append(obj["Key"])
    if s3_prefix in keys:
        keys.remove(s3_prefix)
    return keys


def group_keys_by_collection(keys):
    file_key_dict = {key.split("/")[-1]: key for key in keys}
    file_names = list(file_key_dict.keys())
    file_pattern = r"^\w+\.([\w-]+)\.([\w]+)"
    grouped_files = []
    for pattern, group in groupby(
            file_names, lambda x: re.match(file_pattern, x).group()
    ):
        grouped_files.append({pattern: list(group)})
    list_of_dicts = []
    for x in grouped_files:
        for k, v in x.items():
            gh = []
            for x in v:
                gh.append(file_key_dict[x])
        list_of_dicts.append({k: gh})
    return list_of_dicts


def consolidate_rdd_per_collection(collection, secrets_collections, s3_client,
                                   s3_htme_bucket, spark, keys_map, run_time_stamp,
                                   s3_publish_bucket, published_database_name):
    for collection_name, collection_files_keys in collection.items():
        the_logger.info("Processing collection : %s" % collection_name)
        tag_value = secrets_collections[collection_name.lower()]
        start_time = time.perf_counter()
        rdd_list = []
        for collection_file_key in collection_files_keys:
            encrypted = read_binary(spark,
                                    f"s3://{s3_htme_bucket}/{collection_file_key}"
                                    )
            add_filesize_metric(collection_name, s3_client, s3_htme_bucket, collection_file_key)
            metadata = get_metadatafor_key(collection_file_key, s3_client, s3_htme_bucket)
            ciphertext = metadata["ciphertext"]
            datakeyencryptionkeyid = metadata["datakeyencryptionkeyid"]
            iv = metadata["iv"]
            plain_text_key = get_plaintext_key_calling_dks(
                ciphertext, datakeyencryptionkeyid, keys_map
            )
            decrypted = encrypted.mapValues(
                lambda val, plain_text_key=plain_text_key, iv=iv: decrypt(plain_text_key, iv, val)
            )
            decompressed = decrypted.mapValues(decompress)
            decoded = decompressed.mapValues(decode)
            rdd_list.append(decoded)
        consolidated_rdd = spark.sparkContext.union(rdd_list)
        consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
        the_logger.info("Persisting Json : %s" % collection_name)
        json_location_prefix = "${file_location}/%s/%s/%s" % (
            run_time_stamp,
            get_collection(collection_name),
            get_collection(collection_name) + ".json"
        )
        json_location = "s3://%s/%s" % (
            s3_publish_bucket,
            json_location_prefix
        )
        persist_json(json_location, consolidated_rdd_mapped)
        the_logger.info("Applying Tags for prefix : " + json_location_prefix)
        tag_objects(json_location_prefix, tag_value, s3_client, s3_publish_bucket)
    the_logger.info("Creating Hive tables for : %s" % collection_name)
    create_hive_on_published(spark, json_location, collection_name, published_database_name)
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", collection_name, str(total_time))
    the_logger.info("Completed Processing : %s" % collection_name)


def decode(txt):
    return txt.decode("utf-8")


def get_metadatafor_key(key, s3_client, s3_htme_bucket):
    s3_object = s3_client.get_object(Bucket=s3_htme_bucket, Key=key)
    # print(s3_object)
    iv = s3_object["Metadata"]["iv"]
    ciphertext = s3_object["Metadata"]["ciphertext"]
    datakeyencryptionkeyid = s3_object["Metadata"]["datakeyencryptionkeyid"]
    # print ( "iv " + iv + "ciphertext" + ciphertext + "datakeyencryptionkeyid " + datakeyencryptionkeyid )
    metadata = {
        "iv": iv,
        "ciphertext": ciphertext,
        "datakeyencryptionkeyid": datakeyencryptionkeyid,
    }
    return metadata


def retrieve_secrets():
    secret_name = "${secret_name}"
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    response_binary = response["SecretBinary"]
    response_decoded = response_binary.decode("utf-8")
    response_dict = ast.literal_eval(response_decoded)
    return response_dict


def tag_objects(prefix, tag_value, s3_client, s3_publish_bucket):
    default_value = "default"

    if tag_value is None or tag_value == "":
        tag_value = default_value
    for key in s3_client.list_objects(Bucket=s3_publish_bucket, Prefix=prefix)["Contents"]:
        s3_client.put_object_tagging(
            Bucket=s3_publish_bucket,
            Key=key["Key"],
            Tagging={"TagSet": [{"Key": "collection_tag", "Value": tag_value}]},
        )


def get_plaintext_key_calling_dks(encryptedkey, keyencryptionkeyid, keys_map):
    if keys_map.get(encryptedkey):
        key = keys_map[encryptedkey]
    else:
        key = call_dks(encryptedkey, keyencryptionkeyid)
        keys_map[encryptedkey] = key
    return key


def call_dks(cek, kek):
    url = "${url}"
    params = {"keyId": kek}
    result = requests.post(
        url,
        params=params,
        data=cek,
        cert=(
            "/etc/pki/tls/certs/private_key.crt",
            "/etc/pki/tls/private/private_key.key",
        ),
        verify="/etc/pki/ca-trust/source/anchors/analytical_ca.pem",
    )
    content = result.json()
    return content["plaintextDataKey"]


def read_binary(spark, file_path):
    return spark.sparkContext.binaryFiles(file_path)


def decrypt(plain_text_key, iv_key, data):
    iv_int = int(base64.b64decode(iv_key).hex(), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(plain_text_key), AES.MODE_CTR, counter=ctr)
    decrypted = aes.decrypt(data)
    return decrypted


def decompress(compressed_text):
    return zlib.decompress(compressed_text, 16 + zlib.MAX_WBITS)


def persist_json(json_location, values):
    values.saveAsTextFile(json_location)


def get_collection(collection_name):
    return (
        collection_name.replace("db.", "", 1)
            .replace(".", "_")
            .replace("-", "_")
            .lower()
    )


def get_collections(secrets_response):
    try:
        collections = secrets_response["collections_all"]
        collections = {k.lower(): v.lower() for k, v in collections.items()}
    except:
        logging.error("Problem with collections list")
    return collections


def create_hive_on_published(spark, json_location, collection_name, published_database_name):
    hive_table_name = get_collection(collection_name)
    src_hive_table = published_database_name + "." + hive_table_name
    the_logger.info("Creating Hive tables  : " + src_hive_table)
    src_hive_drop_query = f"DROP TABLE IF EXISTS {src_hive_table}"
    src_hive_create_query = (
        f"""CREATE EXTERNAL TABLE IF NOT EXISTS {src_hive_table}(val STRING) STORED AS TEXTFILE LOCATION "{json_location}" """
    )
    spark.sql(src_hive_drop_query)
    spark.sql(src_hive_create_query)


def add_filesize_metric(collection_name, s3_client, s3_htme_bucket, collection_file_key):
    metadata = s3_client.head_object(Bucket=s3_htme_bucket, Key=collection_file_key)
    add_metric("collection_size.csv", collection_name, metadata['ResponseMetadata']['HTTPHeaders']['content-length'])


def add_metric(metrics_file, collection_name, value):
    metrics_path = f"/opt/emr/metrics/{metrics_file}"
    if not os.path.exists(metrics_path):
        os.mknod(metrics_path)
    with open(metrics_path, "r") as f:
        lines = f.readlines()
    with open(metrics_path, "w") as f:
        for line in lines:
            if not line.startswith(get_collection(collection_name)):
                f.write(line)
        f.write(get_collection(collection_name) + "," + value + "\n")


def get_spark_session():
    spark = (
        SparkSession.builder.master("yarn")
            .config("spark.metrics.conf", "/opt/emr/metrics/metrics.properties")
            .config("spark.metrics.namespace", "adg")
            .appName("spike")
            .enableHiveSupport()
            .getOrCreate()
    )
    spark.conf.set("spark.scheduler.mode", "FAIR")
    return spark


if __name__ == "__main__":
    spark = get_spark_session()
    run_time_stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    published_database_name = "${published_db}"
    s3_htme_bucket = os.getenv("S3_HTME_BUCKET")
    s3_prefix = "${s3_prefix}"
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_client("s3")
    secrets_response = retrieve_secrets()
    secrets_collections = get_collections(secrets_response)
    keys_map = {}
    start_time = time.perf_counter()
    main(spark, s3_client, s3_htme_bucket, s3_prefix, secrets_collections, keys_map, run_time_stamp, s3_publish_bucket,
         published_database_name)
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", "all_collections", str(total_time))
