import ast
import base64
import boto3
import logging
import os
import re
import requests
import zlib
import concurrent.futures
import time
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util import Counter
from itertools import groupby
from logger import setup_logging
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)



def main():
    keys = get_list_keys_for_prefix()
    list_of_dicts = group_keys_by_collection(keys)
    list_of_dicts_filtered = get_collections_in_secrets (list_of_dicts)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(consolidate_rdd_per_collection, list_of_dicts_filtered)

def get_collections_in_secrets(list_of_dicts):
    filtered_list = []
    for collection_dict in list_of_dicts:
        for collection_name, collection_files_keys in collection_dict.items():
            if collection_name.lower() in secrets_collections:
                filtered_list.append(collection_dict)
            else:
                logging.error(
                    collection_name + " is not present in the collections list "
                )
    return filtered_list

def get_client(service_name):
    client = boto3.client(service_name)
    return client

def get_list_keys_for_prefix():
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
    file_pattern = "^\w+\.([\w-]+)\.([\w]+)"
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

def consolidate_rdd_per_collection(collection):
    for collection_name, collection_files_keys in collection.items():
        the_logger.info("Processing collection : " + collection_name)
        tag_value = secrets_collections[collection_name.lower()]
        print(f"Processing Collection {collection_name}")
        start_time = time.perf_counter()
        rdd_list = []
        for collection_file_key in collection_files_keys:
            encrypted = read_binary(
                f"s3://{s3_htme_bucket}/{collection_file_key}"
            )
            add_filesize_metric(collection_name, s3_htme_bucket, collection_file_key)
            metadata = get_metadatafor_key(collection_file_key)
            ciphertext = metadata["ciphertext"]
            datakeyencryptionkeyid = metadata["datakeyencryptionkeyid"]
            iv = metadata["iv"]
            plain_text_key = get_plaintext_key_calling_dks(
                ciphertext, datakeyencryptionkeyid
            )
            decrypted = encrypted.mapValues(
                lambda val, plain_text_key = plain_text_key, iv = iv: decrypt(plain_text_key, iv, val)
            )
            decompressed = decrypted.mapValues(decompress)
            decoded = decompressed.mapValues(decode)
            rdd_list.append(decoded)
        consolidated_rdd = spark.sparkContext.union(rdd_list)
        consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
        the_logger.info("Persisting Json : " + collection_name)
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
        tag_objects(json_location_prefix, tag_value)
    the_logger.info("Creating Hive tables for : " + collection_name)
    create_hive_on_published(json_location, collection_name)
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", collection_name, str(total_time))
    the_logger.info("Completed Processing : " + collection_name)


def decode(txt):
    return  txt.decode("utf-8")

def get_metadatafor_key(key):
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


def tag_objects(prefix, tag_value):
    session = boto3.session.Session()
    client_s3 = session.client(service_name="s3")
    default_value = "default"

    if tag_value is None or tag_value == "":
        tag_value = default_value
    for key in client_s3.list_objects(Bucket=s3_publish_bucket, Prefix=prefix)[
        "Contents"
    ]:
        client_s3.put_object_tagging(
            Bucket=s3_publish_bucket,
            Key=key["Key"],
            Tagging={"TagSet": [{"Key": "collection_tag", "Value": tag_value}]},
        )


def get_plaintext_key_calling_dks(encryptedkey, keyencryptionkeyid):
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


def read_binary(file_path):
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


def get_published_db_name():
    published_database_name = "${published_db}"
    return published_database_name


def get_collections(secrets_response):
    try:
        collections = secrets_response["collections_all"]
        collections = {k.lower(): v.lower() for k, v in collections.items()}
    except:
        logging.error("Problem with collections list")
    return collections


def create_hive_on_published(json_location, collection_name):
    hive_table_name = get_collection(collection_name)
    src_hive_table = published_database_name + "." + hive_table_name
    # print(f'src_hive_table ======={hive_table_name}')
    the_logger.info("Creating Hive tables  : " + src_hive_table)
    src_hive_drop_query = "DROP TABLE IF EXISTS %s" % src_hive_table
    src_hive_create_query = (
        """CREATE EXTERNAL TABLE IF NOT EXISTS %s(val STRING) STORED AS TEXTFILE LOCATION "%s" """
        % (src_hive_table, json_location)
    )
    spark.sql(src_hive_drop_query)
    spark.sql(src_hive_create_query)
    return None

def add_filesize_metric(collection_name, s3_htme_bucket, collection_file_key):
    metadata = s3_client.head_object(Bucket=s3_htme_bucket, Key=collection_file_key)
    add_metric("collection_size.csv", collection_name, metadata['ResponseMetadata']['HTTPHeaders']['content-length'])

def add_metric(metrics_file, collection_name, value):
    metrics_path = "/opt/emr/metrics/" + metrics_file
    if not os.path.exists(metrics_path):
        os.mknod(metrics_path)
    with open(metrics_path, "r") as f:
        lines = f.readlines()
    with open(metrics_path, "w") as f:
        for line in lines:
            if not (line.startswith(get_collection(collection_name))):
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
    published_database_name = get_published_db_name()
    s3_htme_bucket = os.getenv("S3_HTME_BUCKET")
    s3_prefix = "${s3_prefix}"
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_client("s3")
    secrets_response = retrieve_secrets()
    secrets_collections = get_collections(secrets_response)
    keys_map = {}
    start_time = time.perf_counter()
    main()
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", "all_collections", str(total_time))
