import argparse
import ast
import base64
import concurrent.futures
import csv
import itertools
import os
import re
import sys
import time
import zlib
from datetime import datetime
from itertools import groupby

import boto3
import requests
from boto3.dynamodb.conditions import Key
from Crypto.Cipher import AES
from Crypto.Util import Counter

from pyspark.sql import SparkSession
from steps.logger import setup_logging

IN_PROGRESS_STATUS = "In Progress"
FAILED_STATUS = "Failed"
COMPLETED_STATUS = "Completed"
DATA_PRODUCT_NAME = "ADG"
AUDIT_TABLE_HASH_KEY = "Correlation_Id"
AUDIT_TABLE_RANGE_KEY = "Run_Id"

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def get_parameters():
    """Define and parse command line args."""
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job"
    )
    # Parse command line inputs and set defaults
    parser.add_argument("--correlation_id", default="0")
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    args, unrecognized_args = parser.parse_known_args()
    the_logger.warning(
        "Unrecognized args %s found for the correlation id %s",
        unrecognized_args,
        args.correlation_id,
    )
    return args


def main(
    spark,
    s3_client,
    s3_htme_bucket,
    secrets_collections,
    keys_map,
    run_time_stamp,
    s3_publish_bucket,
    published_database_name,
    args,
    run_id,
    s3_resource
):
    try:
        keys = get_list_keys_for_prefix(s3_client, s3_htme_bucket, args.s3_prefix)
        list_of_dicts = group_keys_by_collection(keys)
        list_of_dicts_filtered = get_collections_in_secrets(
            list_of_dicts, secrets_collections, args
        )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            all_processed_collections = executor.map(
                consolidate_rdd_per_collection,
                list_of_dicts_filtered,
                itertools.repeat(secrets_collections),
                itertools.repeat(s3_client),
                itertools.repeat(s3_htme_bucket),
                itertools.repeat(spark),
                itertools.repeat(keys_map),
                itertools.repeat(run_time_stamp),
                itertools.repeat(s3_publish_bucket),
                itertools.repeat(args),
                itertools.repeat(run_id),
                itertools.repeat(s3_resource)
            )
    except Exception as ex:
        the_logger.error(
            "Some error occurred for correlation id : %s %s ",
            args.correlation_id,
            str(ex),
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        # raising exception is not working with YARN so need to send an exit code(-1) for it to fail the job
        sys.exit(-1)
    # Create hive tables only if all the collections have been processed successfully else raise exception
    list_of_processed_collections = list(all_processed_collections)
    if len(list_of_processed_collections) == len(secrets_collections):
        create_hive_tables_on_published(
            spark, list_of_processed_collections, published_database_name, args, run_id
        )
        create_adg_status_csv(
            args.correlation_id, s3_publish_bucket, s3_client, run_time_stamp
        )
    else:
        the_logger.error(
            "Not all collections have been processed looks like there is missing data, stopping Spark for correlation id: %s and run id : %s",
            args.correlation_id,
            run_id,
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        sys.exit(-1)


def get_collections_in_secrets(list_of_dicts, secrets_collections, args):
    filtered_list = []
    for collection_dict in list_of_dicts:
        for collection_name, collection_files_keys in collection_dict.items():
            if collection_name in secrets_collections:
                filtered_list.append(collection_dict)
            else:
                the_logger.warning(
                    "%s is not present in the secret collections list for correlation id : %s",
                    collection_name,
                    args.correlation_id,
                )
    return filtered_list


def get_client(service_name):
    client = boto3.client(service_name)
    return client


def get_resource(service_name):
    return boto3.resource(service_name, region_name="${aws_default_region}")

def get_s3_resource():
    return boto3.resource("s3", region_name="${aws_default_region}")

def get_list_keys_for_prefix(s3_client, s3_htme_bucket, s3_prefix):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_htme_bucket, Prefix=s3_prefix)
    for page in pages:
        for obj in page["Contents"]:
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


def consolidate_rdd_per_collection(
    collection,
    secrets_collections,
    s3_client,
    s3_htme_bucket,
    spark,
    keys_map,
    run_time_stamp,
    s3_publish_bucket,
    args,
    run_id,
    s3_resource
):
    try:
        for collection_name, collection_files_keys in collection.items():
            the_logger.info(
                "Processing collection : %s for correlation id : %s and run id: %s",
                collection_name,
                args.correlation_id,
                run_id,
            )
            tag_value = secrets_collections[collection_name]
            start_time = time.perf_counter()
            rdd_list = []
            for collection_file_key in collection_files_keys:
                encrypted = read_binary(
                    spark, f"s3://{s3_htme_bucket}/{collection_file_key}"
                )
                metadata = get_metadatafor_key(
                    collection_file_key, s3_client, s3_htme_bucket
                )
                ciphertext = metadata["ciphertext"]
                datakeyencryptionkeyid = metadata["datakeyencryptionkeyid"]
                iv = metadata["iv"]
                plain_text_key = get_plaintext_key_calling_dks(
                    ciphertext, datakeyencryptionkeyid, keys_map, args, run_id
                )
                decrypted = encrypted.mapValues(
                    lambda val, plain_text_key=plain_text_key, iv=iv: decrypt(
                        plain_text_key, iv, val, args, run_id
                    )
                )
                decompressed = decrypted.mapValues(decompress)
                decoded = decompressed.mapValues(decode)
                rdd_list.append(decoded)
            consolidated_rdd = spark.sparkContext.union(rdd_list)
            consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
            the_logger.info(
                "Persisting Json of collection : %s for correlation id : %s and run id: %s",
                collection_name,
                args.correlation_id,
                run_id,
            )
            collection_name_key = get_collection(collection_name)
            collection_name_key = collection_name_key.replace("_", "-")
            json_location_prefix = "${file_location}/%s/%s" % (
                run_time_stamp,
                collection_name_key,
            )

            json_location = "s3://%s/%s" % (s3_publish_bucket, json_location_prefix)
            persist_json(json_location, consolidated_rdd_mapped)
            the_logger.info(
                "Applying Tags for prefix : %s for correlation id : %s and run id: %s",
                json_location_prefix,
                args.correlation_id,
                run_id,
            )
            tag_objects(json_location_prefix, tag_value, s3_client, s3_publish_bucket)
        htme_prefix = collection_file_key.rsplit('/',1)[0]
        add_folder_size_metric(collection_name,s3_htme_bucket, htme_prefix,"htme_collection_size.csv",s3_resource)
        add_folder_size_metric(collection_name, s3_publish_bucket, json_location_prefix,"adg_collection_size.csv",s3_resource)
        the_logger.info(
            "Creating Hive tables of collection : %s for correlation id : %s and run id : %s",
            collection_name,
            args.correlation_id,
            run_id,
        )
        end_time = time.perf_counter()
        total_time = round(end_time - start_time)
        add_metric("processing_times.csv", collection_name, str(total_time))
        the_logger.info(
            "Completed Processing of collection : %s for correlation id : %s and run id : %s",
            collection_name,
            args.correlation_id,
            run_id,
        )
        adg_json_prefix = "analytical-dataset/%s" % (run_time_stamp)
        add_folder_size_metric('all_collections',s3_htme_bucket, args.s3_prefix,"htme_collection_size.csv",s3_resource)
        add_folder_size_metric('all_collections', s3_publish_bucket, adg_json_prefix,"adg_collection_size.csv",s3_resource)
    except BaseException as ex:
        the_logger.error(
            "Error processing for correlation id: %s and run id : %s for collection %s %s",
            args.correlation_id,
            run_id,
            collection_name,
            str(ex),
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        sys.exit(-1)
    return (collection_name, json_location)


def decode(txt):
    return txt.decode("utf-8")


def get_metadatafor_key(key, s3_client, s3_htme_bucket):
    s3_object = s3_client.get_object(Bucket=s3_htme_bucket, Key=key)
    # print(s3_object)
    iv = s3_object["Metadata"]["iv"]
    ciphertext = s3_object["Metadata"]["ciphertext"]
    datakeyencryptionkeyid = s3_object["Metadata"]["datakeyencryptionkeyid"]
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
    for key in s3_client.list_objects(Bucket=s3_publish_bucket, Prefix=prefix)[
        "Contents"
    ]:
        s3_client.put_object_tagging(
            Bucket=s3_publish_bucket,
            Key=key["Key"],
            Tagging={"TagSet": [{"Key": "collection_tag", "Value": tag_value}]},
        )


def get_plaintext_key_calling_dks(
    encryptedkey, keyencryptionkeyid, keys_map, args, run_id
):
    if keys_map.get(encryptedkey):
        key = keys_map[encryptedkey]
    else:
        key = call_dks(encryptedkey, keyencryptionkeyid, args, run_id)
        keys_map[encryptedkey] = key
    return key


def call_dks(cek, kek, args, run_id):
    try:
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
    except BaseException as ex:
        the_logger.error(
            "Problem calling DKS for correlation id: %s and run id: %s %s",
            args.correlation_id,
            run_id,
            str(ex),
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        sys.exit(-1)
    return content["plaintextDataKey"]


def read_binary(spark, file_path):
    return spark.sparkContext.binaryFiles(file_path)


def decrypt(plain_text_key, iv_key, data, args, run_id):
    try:
        iv_int = int(base64.b64decode(iv_key).hex(), 16)
        ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
        aes = AES.new(base64.b64decode(plain_text_key), AES.MODE_CTR, counter=ctr)
        decrypted = aes.decrypt(data)
    except BaseException as ex:
        the_logger.error(
            "Problem decrypting data for correlation id and run id: %s %s %s",
            args.correlation_id,
            run_id,
            str(ex),
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        sys.exit(-1)
    return decrypted


def decompress(compressed_text):
    return zlib.decompress(compressed_text, 16 + zlib.MAX_WBITS)


def persist_json(json_location, values):
    values.saveAsTextFile(json_location)


def get_collection(collection_name):
    return collection_name.replace("db.", "", 1).replace(".", "/").replace("-", "_")


def get_collections(secrets_response, args):
    try:
        collections = secrets_response["collections_all"]
        collections = {k: v for k, v in collections.items()}
    except BaseException as ex:
        the_logger.error(
            "Problem with collections list for correlation id : %s %s",
            args.correlation_id,
            str(ex),
        )
        sys.exit(-1)
    return collections


def create_hive_tables_on_published(
    spark, all_processed_collections, published_database_name, args, run_id
):
    try:
        # Check to create database only if the backend is Aurora as Glue database is created through terraform
        if "${hive_metastore_backend}" == "aurora":
            the_logger.info(
                "Creating metastore db while processing correlation_id %s and run id %s",
                args.correlation_id,
                run_id,
            )
            create_db_query = f"CREATE DATABASE IF NOT EXISTS {published_database_name}"
            spark.sql(create_db_query)
        for (collection_name, collection_json_location) in all_processed_collections:
            hive_table_name = get_collection(collection_name)
            hive_table_name = hive_table_name.replace("/", "_")
            src_hive_table = published_database_name + "." + hive_table_name
            the_logger.info(
                "Creating Hive table for : %s for correlation id : %s and run id: %s",
                src_hive_table,
                args.correlation_id,
                run_id,
            )
            src_hive_drop_query = f"DROP TABLE IF EXISTS {src_hive_table}"
            src_hive_create_query = f"""CREATE EXTERNAL TABLE IF NOT EXISTS {src_hive_table}(val STRING) STORED AS TEXTFILE LOCATION "{collection_json_location}" """
            spark.sql(src_hive_drop_query)
            spark.sql(src_hive_create_query)
    except BaseException as ex:
        the_logger.error(
            "Problem with creating Hive tables for correlation id: %s and run id: %s %s ",
            args.correlation_id,
            run_id,
            str(ex),
        )
        log_end_of_batch(args.correlation_id, run_id, FAILED_STATUS)
        sys.exit(-1)


def add_filesize_metric(
    collection_name, s3_client, s3_htme_bucket, collection_file_key
):
    metadata = s3_client.head_object(Bucket=s3_htme_bucket, Key=collection_file_key)
    add_metric(
        "htme_collection_size.csv",
        collection_name,
        metadata["ResponseMetadata"]["HTTPHeaders"]["content-length"],
    )

def add_folder_size_metric(collection_name, s3_bucket, s3_prefix,filename,s3_resource):
    total_size = 0
    for obj in s3_resource.Bucket(s3_bucket).objects.filter(Prefix=s3_prefix):
        total_size += obj.size
    add_metric(
        filename,
        collection_name,
        str(total_size))

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
        collection_name = get_collection(collection_name).replace("/", "_")
        f.write(collection_name + "," + value + "\n")


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


def get_todays_date():
    return datetime.now().strftime("%Y-%m-%d")


def log_start_of_batch(correlation_id, dynamodb=None):
    """Logging start of batch in metadata audit table as In Progress"""
    the_logger.info(
        "Updating audit table with start status for correlation_id %s", correlation_id
    )
    try:
        if not dynamodb:
            dynamodb = get_resource("dynamodb")
        data_pipeline_metadata = "${data_pipeline_metadata}"
        table = dynamodb.Table(data_pipeline_metadata)
        run_id = 1
        response = table.query(
            KeyConditionExpression=Key(AUDIT_TABLE_HASH_KEY).eq(correlation_id),
            ScanIndexForward=False,
        )
        # If this is the first entry for correlation_id then create a new entry with Run_Id as 1 else increment it by 1
        if not response["Items"]:
            put_item(correlation_id, run_id, table, IN_PROGRESS_STATUS)
        else:
            run_id = response["Items"][0][AUDIT_TABLE_RANGE_KEY] + 1
            put_item(correlation_id, run_id, table, IN_PROGRESS_STATUS)
    except BaseException as ex:
        the_logger.error(
            "Problem updating audit table start status for correlation id : %s %s",
            correlation_id,
            str(ex),
        )
        sys.exit(-1)
    return run_id


def put_item(correlation_id, run_id, table, status):
    table.put_item(
        Item={
            AUDIT_TABLE_HASH_KEY: correlation_id,
            AUDIT_TABLE_RANGE_KEY: run_id,
            "Date": get_todays_date(),
            "DataProduct": DATA_PRODUCT_NAME,
            "Status": status,
        }
    )


def log_end_of_batch(correlation_id, run_id, status, dynamodb=None):
    """Logging end of batch in metadata audit table as Completed/Failed"""
    the_logger.info(
        "Updating audit table with end status for correlation_id %s", correlation_id
    )
    try:
        if not dynamodb:
            dynamodb = get_resource("dynamodb")
        data_pipeline_metadata = "${data_pipeline_metadata}"
        table = dynamodb.Table(data_pipeline_metadata)
        put_item(correlation_id, run_id, table, status)
    except BaseException as ex:
        the_logger.error(
            "Problem updating audit table end status for correlation id: %s and run id : %s %s",
            correlation_id,
            run_id,
            str(ex),
        )
        sys.exit(-1)


def create_adg_status_csv(correlation_id, publish_bucket, s3_client, run_time_stamp):
    file_location = "${file_location}"

    with open("adg_params.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["correlation_id", "s3_prefix"])
        writer.writerow([correlation_id, f"{file_location}/{run_time_stamp}"])

    with open("adg_params.csv", "rb") as data:
        s3_client.upload_fileobj(
            data, publish_bucket, f"{file_location}/adg_output/adg_params.csv"
        )


if __name__ == "__main__":
    args = get_parameters()
    the_logger.info(
        "Processing spark job for correlation id : %s" % args.correlation_id
    )
    spark = get_spark_session()
    run_time_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    published_database_name = "${published_db}"
    s3_htme_bucket = os.getenv("S3_HTME_BUCKET")
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_client("s3")
    s3_resource = get_s3_resource()
    secrets_response = retrieve_secrets()
    secrets_collections = get_collections(secrets_response, args)
    keys_map = {}
    start_time = time.perf_counter()
    dynamodb = get_resource("dynamodb")
    run_id = log_start_of_batch(args.correlation_id, dynamodb)
    main(
        spark,
        s3_client,
        s3_htme_bucket,
        secrets_collections,
        keys_map,
        run_time_stamp,
        s3_publish_bucket,
        published_database_name,
        args,
        run_id,
        s3_resource
    )
    log_end_of_batch(args.correlation_id, run_id, COMPLETED_STATUS, dynamodb)
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", "all_collections", str(total_time))
