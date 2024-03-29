import argparse
import ast
import base64
import csv
import itertools
import os
import re
import sys
import time
import zlib
import json
import concurrent.futures
import urllib.request
from datetime import datetime, timedelta
from itertools import groupby

import boto3
import botocore
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from Crypto.Cipher import AES
from Crypto.Util import Counter

from pyspark.sql import SparkSession
from steps.logger import setup_logging
import logging
from steps.resume_step import should_skip_step

SNAPSHOT_TYPE_KEY = "snapshot_type"
VALUE_KEY = "Value"
KEY_KEY = "Key"
ARG_SNAPSHOT_TYPE = "snapshot_type"
ARG_S3_PREFIX = "s3_prefix"
ARG_CORRELATION_ID = "correlation_id"
SNAPSHOT_TYPE_INCREMENTAL = "incremental"
SNAPSHOT_TYPE_FULL = "full"
ARG_SNAPSHOT_TYPE_VALID_VALUES = [SNAPSHOT_TYPE_FULL, SNAPSHOT_TYPE_INCREMENTAL]
TTL_KEY = "TimeToExist"
ADG_STATUS_FIELD_NAME = "ADGStatus"
ADG_CLUSTER_ID_FIELD_NAME = "ADGClusterId"
CORRELATION_ID_DDB_FIELD_NAME = "CorrelationId"
COLLECTION_NAME_DDB_FIELD_NAME = "CollectionName"
TABLE_NAME = "${dynamodb_table_name}"
PIPELINE_METADATA_TABLE = "${data_pipeline_metadata}"
DEFAULT_REGION = "${aws_default_region}"
EXISTING_OUTPUT_PREFIX=False

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


class CollectionException(Exception):
    """Raised when collection could not be published"""

    pass


class CollectionProcessingException(CollectionException):
    """Raised when collection could not be published"""

    pass


class CollectionPublishingException(CollectionException):
    """Raised when collection could not be published"""

    pass


def get_parameters():
    """Define and parse command line args."""
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job"
    )
    # Parse command line inputs and set defaults
    parser.add_argument("--correlation_id", default="0")
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    parser.add_argument("--monitoring_topic_arn", default="${monitoring_topic_arn}")
    parser.add_argument("--snapshot_type", default="full")
    parser.add_argument("--export_date", default=datetime.now().strftime("%Y-%m-%d"))
    args, unrecognized_args = parser.parse_known_args()
    args.snapshot_type = (
        SNAPSHOT_TYPE_INCREMENTAL
        if args.snapshot_type.lower() == SNAPSHOT_TYPE_INCREMENTAL
        else SNAPSHOT_TYPE_FULL
    )

    if len(unrecognized_args) > 0:
        the_logger.warning(
            "Unrecognized args %s found for the correlation id %s",
            unrecognized_args,
            args.correlation_id,
        )

    validate_required_args(args)

    return args


def validate_required_args(args):
    required_args = [ARG_CORRELATION_ID, ARG_S3_PREFIX, ARG_SNAPSHOT_TYPE]
    missing_args = []
    for required_message_key in required_args:
        if required_message_key not in args:
            missing_args.append(required_message_key)
    if missing_args:
        raise argparse.ArgumentError(
            None,
            "ArgumentError: The following required arguments are missing: {}".format(
                ", ".join(missing_args)
            ),
        )
    if args.snapshot_type.lower() not in ARG_SNAPSHOT_TYPE_VALID_VALUES:
        raise argparse.ArgumentError(
            None,
            "ArgumentError: Valid values for snapshot_type are: {}".format(
                ", ".join(ARG_SNAPSHOT_TYPE_VALID_VALUES)
            ),
        )


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
    dynamodb_client,
    sns_client,
    output_prefix,
    s3_resource=None,

):
    try:
        keys = get_list_keys_for_prefix(s3_client, s3_htme_bucket, args.s3_prefix)
        list_of_dicts = group_keys_by_collection(keys)
        if args.snapshot_type.lower() == SNAPSHOT_TYPE_INCREMENTAL:
            populate_empty_prefixes_for_collections_in_secrets_but_no_data(list_of_dicts, secrets_collections, s3_client, output_prefix, s3_publish_bucket)
        list_of_dicts_filtered = get_collections_in_secrets(
            list_of_dicts, secrets_collections, args
        )
        verified_database_name = create_metastore_db(
            spark,
            published_database_name,
            args,
        )
        the_logger.info(
            "Using database name %s",
            verified_database_name,
        )
        process_collections_threaded(
            spark,
            verified_database_name,
            args,
            run_time_stamp,
            dynamodb_client,
            list_of_dicts_filtered,
            secrets_collections,
            s3_client,
            s3_htme_bucket,
            keys_map,
            s3_publish_bucket,
            sns_client,
            output_prefix,
            s3_resource,
        )
    except CollectionException as ex:
        the_logger.error(
            "Some error occurred for correlation id : %s %s ",
            args.correlation_id,
            repr(ex),
        )
        # raising exception is not working with YARN so need to send an exit code(-1) for it to fail the job
        sys.exit(-1)

    create_adg_status_csv(
        args.correlation_id,
        s3_publish_bucket,
        s3_client,
        args.snapshot_type,
        args.export_date,
        output_prefix,
    )


def populate_empty_prefixes_for_collections_in_secrets_but_no_data(list_of_dicts, secrets_collections, s3_client, output_prefix, published_bucket):
    # This method is implemnted to create empty directory when no data for a collection for strategic ingest to work - DW-8004
    collections = []
    empty_str = b''
    for collection_dict in list_of_dicts:
        for collection_name, collection_files_keys in collection_dict.items():
            collections.append(collection_name)
    for k, v in secrets_collections.items():
        if k not in collections:
            collection_name_key = get_collection(k)
            collection_name_key = collection_name_key.replace("_", "-")
            empty_file_key = f'{output_prefix}/{collection_name_key}/empty.txt'
            the_logger.info("Creating a empty directory for the collection %s as there is no data with the prefix", k, empty_file_key)
            s3_client.put_object(Body=empty_str, Bucket=published_bucket, Key=empty_file_key)


def process_collections_threaded(
    spark,
    verified_database_name,
    args,
    run_time_stamp,
    dynamodb_client,
    list_of_dicts_filtered,
    secrets_collections,
    s3_client,
    s3_htme_bucket,
    keys_map,
    s3_publish_bucket,
    sns_client,
    output_prefix,
    s3_resource=None,
):
    all_processed_collections = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        completed_collections = executor.map(
            process_collection,
            itertools.repeat(spark),
            itertools.repeat(verified_database_name),
            itertools.repeat(args),
            itertools.repeat(run_time_stamp),
            itertools.repeat(dynamodb_client),
            list_of_dicts_filtered,
            itertools.repeat(secrets_collections),
            itertools.repeat(s3_client),
            itertools.repeat(s3_htme_bucket),
            itertools.repeat(keys_map),
            itertools.repeat(s3_publish_bucket),
            itertools.repeat(sns_client),
            itertools.repeat(output_prefix),
            itertools.repeat(s3_resource),
        )

    for completed_collection in completed_collections:
        all_processed_collections.append(completed_collection)

    return all_processed_collections


def create_metastore_db(
    spark,
    published_database_name,
    args,
):
    verified_database_name = published_database_name
    # Check to create database only if the backend is Aurora as Glue database is created through terraform
    if "${hive_metastore_backend}" == "aurora":
        try:
            if args.snapshot_type.lower() != SNAPSHOT_TYPE_FULL:
                verified_database_name = (
                    f"{published_database_name}_{SNAPSHOT_TYPE_INCREMENTAL}"
                )

            the_logger.info(
                "Creating metastore db with name of %s while processing correlation_id %s",
                verified_database_name,
                args.correlation_id,
            )

            create_db_query = f"CREATE DATABASE IF NOT EXISTS {verified_database_name}"
            spark.sql(create_db_query)
        except BaseException as ex:
            the_logger.error(
                "Error occurred creating hive metastore backend %s",
                repr(ex),
            )
            raise BaseException(ex)

    return verified_database_name


def process_collection(
    spark,
    verified_database_name,
    args,
    run_time_stamp,
    dynamodb_client,
    collection,
    secrets_collections,
    s3_client,
    s3_htme_bucket,
    keys_map,
    s3_publish_bucket,
    sns_client,
    output_prefix,
    s3_resource=None,
):
    if s3_resource is None:
        s3_resource = get_s3_resource()

    collection_pairs = collection.items()
    collection_iterator = iter(collection_pairs)
    (collection_name, collection_files_keys) = next(collection_iterator)

    update_adg_status_for_collection(
        dynamodb_client,
        TABLE_NAME,
        args.correlation_id,
        collection_name,
        "Processing",
    )

    try:
        collection_json_location = consolidate_rdd_per_collection(
            collection_name,
            collection_files_keys,
            secrets_collections,
            s3_client,
            s3_htme_bucket,
            spark,
            keys_map,
            run_time_stamp,
            s3_publish_bucket,
            args,
            output_prefix,
            s3_resource,
        )
    except Exception as ex:
        the_logger.error(
            "Error occurred processing collection named %s for correlation id: %s %s",
            collection_name,
            args.correlation_id,
            repr(ex),
        )
        update_adg_status_for_collection(
            dynamodb_client,
            TABLE_NAME,
            args.correlation_id,
            collection_name,
            "Failed_Processing",
        )
        notify_of_collection_failure(
            sns_client,
            args.monitoring_topic_arn,
            args.correlation_id,
            collection_name,
            "Failed_Processing",
            args.snapshot_type,
        )
        raise CollectionProcessingException(ex)

    update_adg_status_for_collection(
        dynamodb_client,
        TABLE_NAME,
        args.correlation_id,
        collection_name,
        "Publishing",
    )

    try:
        create_hive_table_on_published_for_collection(
            spark,
            collection_name,
            collection_json_location,
            verified_database_name,
            args,
            s3_publish_bucket
        )
    except Exception as ex:
        the_logger.error(
            "Error occurred publishing collection named %s for correlation id: %s %s",
            collection_name,
            args.correlation_id,
            repr(ex),
        )
        update_adg_status_for_collection(
            dynamodb_client,
            TABLE_NAME,
            args.correlation_id,
            collection_name,
            "Failed_Publishing",
        )
        notify_of_collection_failure(
            sns_client,
            args.monitoring_topic_arn,
            args.correlation_id,
            collection_name,
            "Failed_Publishing",
            args.snapshot_type,
        )
        raise CollectionPublishingException(ex)

    update_adg_status_for_collection(
        dynamodb_client,
        TABLE_NAME,
        args.correlation_id,
        collection_name,
        "Completed",
    )


def consolidate_rdd_per_collection(
    collection_name,
    collection_files_keys,
    secrets_collections,
    s3_client,
    s3_htme_bucket,
    spark,
    keys_map,
    run_time_stamp,
    s3_publish_bucket,
    args,
    output_prefix,
    s3_resource,
):
    the_logger.info(
        "Processing collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    tag_value = secrets_collections[collection_name]
    start_time = time.perf_counter()
    rdd_list = []
    total_collection_size = 0
    for collection_file_key in collection_files_keys:
        encrypted = read_binary(spark, f"s3://{s3_htme_bucket}/{collection_file_key}")
        metadata = get_metadatafor_key(collection_file_key, s3_client, s3_htme_bucket)
        total_collection_size += get_filesize(
            s3_client, s3_htme_bucket, collection_file_key
        )
        ciphertext = metadata["ciphertext"]
        datakeyencryptionkeyid = metadata["datakeyencryptionkeyid"]
        iv = metadata["iv"]
        plain_text_key = get_plaintext_key_calling_dks(
            ciphertext, datakeyencryptionkeyid, keys_map, args, run_time_stamp
        )
        decrypted = encrypted.mapValues(
            lambda val, plain_text_key=plain_text_key, iv=iv: decrypt(
                plain_text_key, iv, val, args, run_time_stamp
            )
        )
        decompressed = decrypted.mapValues(decompress)
        decoded = decompressed.mapValues(decode)
        rdd_list.append(decoded)
    consolidated_rdd = spark.sparkContext.union(rdd_list)
    collection_name_key = get_collection(collection_name)
    collection_name_key = collection_name_key.replace("_", "-")
    if collection_name_key == "data/businessAudit" or collection_name_key == "data/equality":
        consolidated_rdd = consolidated_rdd.repartition(1)
    consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
    the_logger.info(
        "Persisting Json of collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    file_location = "${file_location}"
    if collection_name_key == "data/businessAudit" or collection_name_key == "data/equality":
        current_date = args.export_date
        json_location_prefix = f"{file_location}/{collection_name_key}/{current_date}/"
        json_location = f"s3://{s3_publish_bucket}/{json_location_prefix}"
        delete_existing_s3_files(s3_publish_bucket, json_location_prefix, s3_client)
    else:
        json_location_prefix = f"{output_prefix}/{collection_name_key}/"
        if EXISTING_OUTPUT_PREFIX:
            #Delete files in prefix if this is a re-run for a failed run
            delete_existing_s3_files(s3_publish_bucket, json_location_prefix, s3_client)
        json_location = f"s3://{s3_publish_bucket}/{json_location_prefix}"
        the_logger.info(f"Using output json location: {json_location}")

    persist_json(json_location, consolidated_rdd_mapped)
    the_logger.info(
        "Applying Tags for prefix : %s for correlation id : %s",
        json_location_prefix,
        args.correlation_id,
    )
    tag_objects(
        json_location_prefix,
        tag_value,
        s3_client,
        s3_publish_bucket,
        args.snapshot_type,
    )
    add_metric("htme_collection_size.csv", collection_name, str(total_collection_size))
    add_folder_size_metric(
        collection_name,
        s3_publish_bucket,
        json_location_prefix,
        "adg_collection_size.csv",
        s3_resource,
    )
    the_logger.info(
        "Created Hive tables of collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", collection_name, str(total_time))
    the_logger.info(
        "Completed Processing of collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    adg_json_prefix = f"{file_location}/{args.snapshot_type.lower()}/{run_time_stamp}"
    add_folder_size_metric(
        "all_collections",
        s3_htme_bucket,
        args.s3_prefix,
        "htme_collection_size.csv",
        s3_resource,
    )
    add_folder_size_metric(
        "all_collections",
        s3_publish_bucket,
        adg_json_prefix,
        "adg_collection_size.csv",
        s3_resource,
    )
    return json_location


def delete_existing_s3_files(s3_bucket, s3_prefix, s3_client):
    """Deletes files if exists in the given bucket and prefix

    Keyword arguments:
    s3_bucket -- the S3 bucket name
    s3_prefix -- the key to look for, could be a file path and key or simply a path
    s3_client -- S3 client
    """
    keys = get_list_keys_for_prefix(s3_client, s3_bucket, s3_prefix)
    the_logger.info(
        "Retrieved '%s' keys from prefix '%s'",
        str(len(keys)),
        s3_prefix,
    )

    waiter = s3_client.get_waiter("object_not_exists")
    for key in keys:
        s3_client.delete_object(Bucket=s3_bucket, Key=key)
        waiter.wait(
            Bucket=s3_bucket, Key=key, WaiterConfig={"Delay": 1, "MaxAttempts": 10}
        )


def create_hive_table_on_published_for_collection(
    spark,
    collection_name,
    collection_json_location,
    verified_database_name,
    args,
    s3_publish_bucket
):
    hive_table_name = get_collection(collection_name)
    hive_table_name = hive_table_name.replace("/", "_")
    src_hive_table = verified_database_name + "." + hive_table_name
    the_logger.info(
        "Publishing collection named : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    if hive_table_name == "data_businessAudit":
        verified_database_name_for_audit = 'uc_dw_auditlog'
        date_hyphen = args.export_date
        date_underscore = date_hyphen.replace("-", "_")
        create_db_query = f"CREATE DATABASE IF NOT EXISTS {verified_database_name_for_audit}"
        the_logger.info(
            "Creating audit database named : %s using sql : '%s' for correlation id : %s",
            verified_database_name_for_audit,
            create_db_query,
            args.correlation_id,
        )
        spark.sql(create_db_query)
        process_audit(
            spark,
            verified_database_name_for_audit,
            date_hyphen,
            date_underscore,
            collection_json_location,
            args,
            s3_publish_bucket
        )
    elif hive_table_name == "data_equality":
        verified_database_name_for_equality = 'uc_equality'
        date_hyphen = args.export_date
        date_underscore = date_hyphen.replace("-", "_")
        create_db_query = f"CREATE DATABASE IF NOT EXISTS {verified_database_name_for_equality} LOCATION 's3://{s3_publish_bucket}/data/uc_equality/'"
        the_logger.info(
            "Creating equality database named : %s using sql : '%s' for correlation id : %s",
            verified_database_name_for_equality,
            create_db_query,
            args.correlation_id,
        )
        spark.sql(create_db_query)
        process_equality(
            spark,
            verified_database_name_for_equality,
            date_hyphen,
            date_underscore,
            collection_json_location,
            args,
        )
    else:
        src_hive_drop_query = f"DROP TABLE IF EXISTS {src_hive_table}"
        src_hive_create_query = f"""CREATE EXTERNAL TABLE IF NOT EXISTS {src_hive_table}(val STRING) STORED AS TEXTFILE LOCATION "{collection_json_location}" """
        spark.sql(src_hive_drop_query)
        spark.sql(src_hive_create_query)
        the_logger.info(
            "Published collection named : %s for correlation id : %s",
            collection_name,
            args.correlation_id,
        )
    return collection_name


def process_audit(
    spark,
    verified_database_name,
    date_hyphen,
    date_underscore,
    collection_json_location,
    args,
    s3_publish_bucket
):
    the_logger.info(
        "Creating audit raw managed table for correlation id : %s",
        args.correlation_id,
    )
    create_audit_log_raw_managed_table(spark, verified_database_name, date_hyphen, collection_json_location)

    auditlog_managed_table_sql_file = get_audit_managed_file()
    auditlog_managed_table_sql_content = (
        auditlog_managed_table_sql_file.read().replace(
            "#{hivevar:auditlog_database}", verified_database_name
        )
    )
    the_logger.info(
        "Creating audit managed table using sql : '%s' for correlation id : %s",
        auditlog_managed_table_sql_content,
        args.correlation_id,
    )
    spark.sql(auditlog_managed_table_sql_content)

    the_logger.info(
        "Creating audit external table for correlation id : %s",
        args.correlation_id,
    )
    auditlog_external_table_sql_file = get_audit_external_file()
    queries = (
        auditlog_external_table_sql_file.read()
        .replace("#{hivevar:auditlog_database}", verified_database_name)
        .replace("#{hivevar:date_underscore}", date_underscore)
        .replace("#{hivevar:date_hyphen}", date_hyphen)
        .replace("#{hivevar:serde}", "org.openx.data.jsonserde.JsonSerDe")
        .replace("#{hivevar:data_location}", collection_json_location)
    )
    execute_queries(queries.split(";"), "audit", spark, args)
    process_auditlog_sec_and_red_v(spark, verified_database_name, date_hyphen, s3_publish_bucket, args)


def process_auditlog_sec_and_red_v(spark,verified_database_name,date_hyphen,s3_publish_bucket, args):
    sec_v_location = f's3://{s3_publish_bucket}/data/uc/auditlog_sec_v/'
    sec_v_columns = get_auditlog_sec_v_columns_file().read().strip('\n')
    sec_v_create_file = get_auditlog_sec_v_create_file()
    sec_v_create_query = sec_v_create_file.read().replace("#{hivevar:uc_database}", "uc").replace("#{hivevar:location_str}", sec_v_location)
    spark.sql(sec_v_create_query)
    sec_v_alter_file = get_auditlog_sec_v_alter_file()
    sec_v_alter_query = sec_v_alter_file.read().replace("#{hivevar:uc_database}", "uc").replace("#{hivevar:date_hyphen}", date_hyphen).replace("#{hivevar:uc_dw_auditlog_database}", verified_database_name).replace("#{hivevar:auditlog_sec_v_columns}", sec_v_columns).replace("#{hivevar:location_str}", sec_v_location)
    execute_queries(sec_v_alter_query.split(";"), "sec_v", spark, args)

    red_v_location = f's3://{s3_publish_bucket}/data/uc/auditlog_red_v/'
    red_v_columns = get_auditlog_red_v_columns_file().read().strip('\n')
    red_v_create_file = get_auditlog_red_v_create_file()
    red_v_create_query = red_v_create_file.read().replace("#{hivevar:uc_database}", "uc").replace("#{hivevar:location_str}", red_v_location)
    spark.sql(red_v_create_query)
    red_v_alter_file = get_auditlog_red_v_alter_file()
    red_v_alter_query = red_v_alter_file.read().replace("#{hivevar:uc_database}", "uc").replace("#{hivevar:date_hyphen}", date_hyphen).replace("#{hivevar:uc_dw_auditlog_database}", verified_database_name).replace("#{hivevar:auditlog_red_v_columns}", red_v_columns).replace("#{hivevar:location_str}", red_v_location)
    execute_queries(red_v_alter_query.split(";"), "red_v", spark, args)


def process_equality(
    spark,
    verified_database_name,
    date_hyphen,
    date_underscore,
    collection_json_location,
    args,
):
    the_logger.info(
        "Creating equality external table for correlation id : %s",
        args.correlation_id,
    )
    equality_external_table_sql_file = get_equality_external_file()
    queries = (
        equality_external_table_sql_file.read()
        .replace("#{hivevar:equality_database}", verified_database_name)
        .replace("#{hivevar:date_underscore}", date_underscore)
        .replace("#{hivevar:date_hyphen}", date_hyphen)
        .replace("#{hivevar:serde}", "org.openx.data.jsonserde.JsonSerDe")
        .replace("#{hivevar:data_location}", collection_json_location)
    )
    execute_queries(queries.split(";"), "equality", spark, args)


def execute_queries(queries, type_of_query, spark, args):
    for query in queries:
        if query and not query.isspace():
            the_logger.info(
                "Executing %s query : '%s' for correlation id : %s",
                type_of_query,
                query,
                args.correlation_id,
            )
            spark.sql(query)
        else:
            the_logger.info(
                "Not executing invalid %s query : '%s' for correlation id : %s",
                type_of_query,
                query,
                args.correlation_id,
            )


def create_audit_log_raw_managed_table(spark, verified_database_name, date_hyphen, collection_json_location):
    the_logger.info(
                "collection_json_location : %s",
                collection_json_location,
            )
    src_managed_hive_table = verified_database_name + "." + 'auditlog_raw'
    src_managed_hive_create_query = f"""CREATE TABLE IF NOT EXISTS {src_managed_hive_table}(val STRING) PARTITIONED BY (date_str STRING) STORED AS orc TBLPROPERTIES ('orc.compress'='ZLIB')"""
    spark.sql(src_managed_hive_create_query)

    date_underscore = date_hyphen.replace("-", "_")
    src_external_table = f'auditlog_raw_external_{date_underscore}'
    src_external_hive_table = verified_database_name + "." + src_external_table
    src_external_hive_create_query = f"""CREATE EXTERNAL TABLE {src_external_hive_table}(val STRING) PARTITIONED BY (date_str STRING) STORED AS TEXTFILE LOCATION "{collection_json_location}" """
    the_logger.info("hive create query %s", src_external_hive_create_query)
    src_external_hive_alter_query = f"""ALTER TABLE {src_external_hive_table} ADD IF NOT EXISTS PARTITION(date_str='{date_hyphen}') LOCATION '{collection_json_location}'"""
    src_external_hive_insert_query = f"""INSERT OVERWRITE TABLE {src_managed_hive_table} SELECT * FROM {src_external_hive_table}"""
    src_external_hive_drop_query = f"""DROP TABLE IF EXISTS {src_external_hive_table}"""

    spark.sql(src_external_hive_drop_query)
    spark.sql(src_external_hive_create_query)
    spark.sql(src_external_hive_alter_query)
    spark.sql(src_external_hive_insert_query)
    spark.sql(src_external_hive_drop_query)


def get_audit_managed_file():
    return open("/var/ci/auditlog_managed_table.sql")

def get_audit_external_file():
    return open("/var/ci/auditlog_external_table.sql")

def get_equality_managed_file():
    return open("/var/ci/equality_managed_table.sql")

def get_equality_external_file():
    return open("/var/ci/equality_external_table.sql")

def get_auditlog_sec_v_create_file():
    return open("/var/ci/create_auditlog_sec_v.sql")

def get_auditlog_sec_v_alter_file():
    return open("/var/ci/alter_add_part_auditlog_sec_v.sql")

def get_auditlog_sec_v_columns_file():
    return open("/var/ci/auditlog_sec_v_columns.txt")

def get_auditlog_red_v_create_file():
    return open("/var/ci/create_auditlog_red_v.sql")

def get_auditlog_red_v_alter_file():
    return open("/var/ci/alter_add_part_auditlog_red_v.sql")

def get_auditlog_red_v_columns_file():
    return open("/var/ci/auditlog_red_v_columns.txt")



def get_filesize(s3_client, s3_htme_bucket, collection_file_key):
    metadata = s3_client.head_object(Bucket=s3_htme_bucket, Key=collection_file_key)
    filesize = metadata["ResponseMetadata"]["HTTPHeaders"]["content-length"]
    return int(filesize)


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


def get_s3_client():
    client_config = botocore.config.Config(
        max_pool_connections=100, retries={"max_attempts": 10, "mode": "standard"}
    )
    client = boto3.client("s3", config=client_config)
    return client


def get_dynamodb_client():
    client_config = botocore.config.Config(
        max_pool_connections=100, retries={"max_attempts": 10, "mode": "standard"}
    )
    client = boto3.client("dynamodb", region_name=DEFAULT_REGION, config=client_config)
    return client


def get_sns_client():
    client_config = botocore.config.Config(
        max_pool_connections=100, retries={"max_attempts": 10, "mode": "standard"}
    )
    client = boto3.client("sns", region_name=DEFAULT_REGION, config=client_config)
    return client


def get_s3_resource():
    session = boto3.session.Session()
    return session.resource("s3", region_name=DEFAULT_REGION)


def get_list_keys_for_prefix(s3_client, s3_bucket, s3_prefix):
    the_logger.info(
        "Looking for files to process in bucket : %s with prefix : %s",
        s3_bucket,
        s3_prefix,
    )
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_bucket, Prefix=s3_prefix)
    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                keys.append(obj["Key"])
    if s3_prefix in keys:
        keys.remove(s3_prefix)
    return keys


def group_keys_by_collection(keys):
    file_key_dict = {key.split("/")[-1]: key for key in keys}
    file_names = list(file_key_dict.keys())
    file_pattern = r"^(?:db.)?([\w-]+)\.([A-Za-z]+-?[A-Za-z]+)"
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


def decode(txt):
    decoded =  txt.decode("utf-8")
    if "\n" == decoded[-1]:
        return decoded[:-1]
    return decoded

def get_metadatafor_key(key, s3_client, s3_htme_bucket):
    instance_id = (
        urllib.request.urlopen("http://169.254.169.254/latest/meta-data/instance-id")
        .read()
        .decode()
    )
    the_logger.debug("Instance id making boto3 get_object calls: %s ", instance_id)
    s3_object = s3_client.get_object(Bucket=s3_htme_bucket, Key=key)
    iv = s3_object["Metadata"]["iv"]
    ciphertext = s3_object["Metadata"]["ciphertext"]
    datakeyencryptionkeyid = s3_object["Metadata"]["datakeyencryptionkeyid"]
    metadata = {
        "iv": iv,
        "ciphertext": ciphertext,
        "datakeyencryptionkeyid": datakeyencryptionkeyid,
    }
    return metadata


def retrieve_secrets(args, secret_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    response_binary = response["SecretBinary"]
    response_decoded = response_binary.decode("utf-8")
    response_dict = ast.literal_eval(response_decoded)
    return response_dict


def tag_objects(prefix, tag_value, s3_client, s3_publish_bucket, snapshot_type):
    the_logger.info(
        "Looking for files to tag in bucket : %s with prefix : %s",
        s3_publish_bucket,
        prefix,
    )
    for key in s3_client.list_objects(Bucket=s3_publish_bucket, Prefix=prefix)[
        "Contents"
    ]:
        tags_set_value = (
            [{"Key": "collection_tag", "Value": "NOT_SET"}]
            if tag_value is None or tag_value == ""
            else get_tags(tag_value, snapshot_type)
        )

        s3_client.put_object_tagging(
            Bucket=s3_publish_bucket,
            Key=key["Key"],
            Tagging={"TagSet": tags_set_value},
        )
    the_logger.info(f"Successfully tagged objects for the following prefix: {prefix}")


def get_tags(tag_value, snapshot_type):
    tag_set = []
    for k, v in tag_value.items():
        tag_set.append({KEY_KEY: k, VALUE_KEY: v})
    tag_set.append({KEY_KEY: SNAPSHOT_TYPE_KEY, VALUE_KEY: snapshot_type})
    return tag_set


def get_plaintext_key_calling_dks(
    encryptedkey, keyencryptionkeyid, keys_map, args, run_time_stamp
):
    if keys_map.get(encryptedkey):
        key = keys_map[encryptedkey]
    else:
        key = call_dks(encryptedkey, keyencryptionkeyid, args, run_time_stamp)
        keys_map[encryptedkey] = key
    return key


def retry_requests(retries=10, backoff=1):
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=frozenset(["POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    requests_session = requests.Session()
    requests_session.mount("https://", adapter)
    requests_session.mount("http://", adapter)
    return requests_session


def call_dks(cek, kek, args, run_time_stamp):
    try:
        url = "${url}"
        params = {"keyId": kek, "correlationId": args.correlation_id}
        result = retry_requests().post(
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
            "Problem calling DKS for correlation id: %s %s",
            args.correlation_id,
            repr(ex),
        )
        sys.exit(-1)
    return content["plaintextDataKey"]


def read_binary(spark, file_path):
    return spark.sparkContext.binaryFiles(file_path)


def decrypt(plain_text_key, iv_key, data, args, run_time_stamp):
    try:
        iv_int = int(base64.b64decode(iv_key).hex(), 16)
        ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
        aes = AES.new(base64.b64decode(plain_text_key), AES.MODE_CTR, counter=ctr)
        decrypted = aes.decrypt(data)
    except BaseException as ex:
        the_logger.error(
            "Problem decrypting data for correlation id %s %s",
            args.correlation_id,
            repr(ex),
        )
        sys.exit(-1)
    return decrypted


def decompress(compressed_text):
    return zlib.decompress(compressed_text, 16 + zlib.MAX_WBITS)


def persist_json(json_location, values):
    values.saveAsTextFile(
        json_location, compressionCodecClass="com.hadoop.compression.lzo.LzopCodec"
    )


def get_collection(collection_name):
    return collection_name.replace("db.", "", 1).replace(".", "/").replace("-", "_")


def get_failed_collection_names(correlation_id, dynamodb_client) -> list:
    failed_collections_response = dynamodb_client.query(
        TableName=TABLE_NAME,
        KeyConditionExpression=f"CorrelationId = :cid",
        FilterExpression="begins_with(ADGStatus, :status)",
        ExpressionAttributeValues={
            ":cid": {"S": correlation_id},
            ":status": {"S": "Failed"},
        }
    )
    collections = [
        failed_collection["CollectionName"]["S"]
        for failed_collection in failed_collections_response["Items"]
    ]
    return collections


def get_collections(secrets_response, args, dynamodb_client):
    try:
        collections = secrets_response["collections_all"]
        collections = {k: v for k, v in collections.items()}

        if EXISTING_OUTPUT_PREFIX:
            the_logger.warning("Running failed collections only")
            failed_collections = get_failed_collection_names(
                args.correlation_id,
                dynamodb_client
            )

            failed_collections_to_process = {}

            for k, v in collections.items():
                if k in failed_collections:
                    failed_collections_to_process[k] = v
                    the_logger.warning(f"{k} is a failed collection, will be processed")
                else:
                    the_logger.warning(
                        f"{k} is not a failed collection, will not be processed"
                    )
            collections = failed_collections_to_process
            if not collections:
                the_logger.warning("No failed collections were found")

    except BaseException as ex:
        the_logger.error(
            "Problem with collections list for correlation id : %s %s",
            args.correlation_id,
            repr(ex),
        )
        sys.exit(-1)
    return collections


def add_filesize_metric(
    collection_name, s3_client, s3_htme_bucket, collection_file_key
):
    metadata = s3_client.head_object(Bucket=s3_htme_bucket, Key=collection_file_key)
    add_metric(
        "htme_collection_size.csv",
        collection_name,
        metadata["ResponseMetadata"]["HTTPHeaders"]["content-length"],
    )


def add_folder_size_metric(
    collection_name, s3_bucket, s3_prefix, filename, s3_resource
):
    the_logger.info(f"Adding folder size metrics for prefix: {s3_prefix}")
    total_size = 0
    for obj in s3_resource.Bucket(s3_bucket).objects.filter(Prefix=s3_prefix):
        total_size += obj.size
    add_metric(filename, collection_name, str(total_size))


def add_metric(metrics_file, collection_name, value):
    try:
        path = "/opt/emr/metrics/"
        if not os.path.exists(path):
            os.makedirs(path)
        metrics_path = f"{path}{metrics_file}"
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
    except Exception as ex:
        the_logger.warn(
            "Problem adding metric with file of '%s', collection name of '%s' and exception of '%s'",
            metrics_file,
            collection_name,
            repr(ex),
        )


def get_spark_session(args):
    spark = (
        SparkSession.builder.master("yarn")
        .config("spark.metrics.conf", "/opt/emr/metrics/metrics.properties")
        .config("spark.metrics.namespace", f"adg_{args.snapshot_type.lower()}")
        .config("spark.executor.heartbeatInterval", "300000")
        .config("spark.storage.blockManagerSlaveTimeoutMs", "500000")
        .config("spark.network.timeout", "500000")
        .config("spark.hadoop.fs.s3.maxRetries", "20")
        .config("spark.rpc.numRetries", "10")
        .config("spark.task.maxFailures", "10")
        .config("spark.scheduler.mode", "FAIR")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .appName("spike")
        .enableHiveSupport()
        .getOrCreate()
    )
    return spark


def get_cluster_id():
    cluster_id = "NOT_SET"
    file_name = "/mnt/var/lib/info/job-flow.json"

    if os.path.isfile(file_name):
        with open(file_name, "r") as file_to_open:
            flow_json = json.loads(file_to_open.read())
            cluster_id = flow_json["jobFlowId"].replace('"', "")

    return cluster_id


def create_adg_status_csv(
    correlation_id,
    publish_bucket,
    s3_client,
    snapshot_type,
    export_date,
    output_prefix,
):
    file_location = "${file_location}"
    with open("adg_params.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["correlation_id", "s3_prefix", "snapshot_type", "export_date"])
        writer.writerow(
            [
                correlation_id,
                output_prefix,
                snapshot_type,
                export_date,
            ]
        )

    with open("adg_params.csv", "rb") as data:
        s3_client.upload_fileobj(
            data,
            publish_bucket,
            f"{file_location}/{snapshot_type}/adg_output/adg_params.csv",
        )


def exit_if_skipping_step():
    if should_skip_step(the_logger, "spark-submit"):
        the_logger.info("Step needs to be skipped so will exit without error")
        sys.exit(0)


def save_output_location(output_prefix):
    the_logger.info(f"Output locations set as {output_prefix}")

    with open("/opt/emr/output_location.txt", "wt") as output_location_file:
        output_location_file.write(output_prefix)

def get_output_prefix(args, dynamodb_client, run_time_stamp):
    DATA_PRODUCT = f"ADG-{args.snapshot_type.lower()}"
    key_dict = {
        "Correlation_Id": {"S": f"{args.correlation_id}"},
        "DataProduct": {"S": f"{DATA_PRODUCT}"},
    }
    the_logger.info(f"looking for {args.correlation_id} and {DATA_PRODUCT} in dynamodbtable {PIPELINE_METADATA_TABLE}")
    try:
        #check for previous run prefix in dynamodb
        output_prefix = dynamodb_client.get_item(TableName=PIPELINE_METADATA_TABLE, Key=key_dict)["Item"]["S3_Prefix_Analytical_DataSet"]["S"]
        global EXISTING_OUTPUT_PREFIX
        EXISTING_OUTPUT_PREFIX = True
        the_logger.info(f"Existing output prefix for ADG previous run: {output_prefix}")
    except:
        file_location = "${file_location}"
        output_prefix = f"{file_location}/{args.snapshot_type.lower()}/{run_time_stamp}"
        the_logger.info(f"No previous run found. Using new prefix for output {output_prefix}")

    return output_prefix

def update_adg_status_for_collection(
    dynamodb_client,
    ddb_export_table,
    correlation_id,
    collection_name,
    status,
):
    the_logger.info(
        f'Updating collection status in dynamodb", "ddb_export_table": "{ddb_export_table}", "correlation_id": '
        + f'"{correlation_id}", "collection_name": "{collection_name}", "status": "{status}'
    )

    dynamodb_client.update_item(
        TableName=ddb_export_table,
        Key={
            CORRELATION_ID_DDB_FIELD_NAME: {"S": correlation_id},
            COLLECTION_NAME_DDB_FIELD_NAME: {"S": collection_name},
        },
        UpdateExpression=f"SET {ADG_STATUS_FIELD_NAME} = :a",
        ExpressionAttributeValues={":a": {"S": status}},
        ReturnValues="ALL_NEW",
    )

    the_logger.info(
        f'Updated collection status in dynamodb", "ddb_export_table": "{ddb_export_table}", "correlation_id": '
        + f'"{correlation_id}", "status": "{status}", "collection_name": "{collection_name}'
    )


def notify_of_collection_failure(
    sns_client,
    sns_topic_arn,
    correlation_id,
    collection_name,
    status,
    snapshot_type,
):
    the_logger.info(
        f'Notifying of failed collection", "sns_topic_arn": "{sns_topic_arn}", "correlation_id": '
        + f'"{correlation_id}", "collection_name": "{collection_name}", "snapshot_type": '
        + f'"{snapshot_type}", "status": "{status}'
    )

    custom_elements = [
        {"key": "Collection Name", "value": collection_name},
        {"key": "Collection Status", "value": status},
        {"key": "Correlation Id", "value": correlation_id},
        {"key": "Snapshot Type", "value": snapshot_type},
    ]

    payload = {
        "severity": "High",
        "notification_type": "Error",
        "slack_username": f"ADG-{snapshot_type.lower()}",
        "title_text": "Collection set to failure status",
        "custom_elements": custom_elements,
    }

    json_message = json.dumps(payload)

    response = None
    try:
        response = sns_client.publish(TopicArn=sns_topic_arn, Message=json_message)
    except Exception as ex:
        the_logger.warning(
            f'Notification failed", "sns_topic_arn": "{sns_topic_arn}", "correlation_id": '
            + f'"{correlation_id}", "collection_name": "{collection_name}", "snapshot_type": '
            + f'"{snapshot_type}", "status": "{status}", "error": "{repr(ex)}'
        )

    the_logger.info(
        f'Notified of failed collection", "sns_topic_arn": "{sns_topic_arn}", "correlation_id": '
        + f'"{correlation_id}", "collection_name": "{collection_name}", "snapshot_type": '
        + f'"{snapshot_type}", "status": "{status}'
    )

    return response


if __name__ == "__main__":
    args = get_parameters()
    the_logger.info(
        "Processing spark job for correlation id : %s, export date : %s, snapshot_type : %s and s3_prefix : %s",
        args.correlation_id,
        args.export_date,
        args.snapshot_type.lower(),
        args.s3_prefix,
    )

    the_logger.info("Checking if step should be skipped")
    exit_if_skipping_step()

    spark = get_spark_session(args)
    run_time_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    published_database_name = "${published_db}"
    secret_name_full = "${secret_name_full}"
    secret_name_incremental = "${secret_name_incremental}"
    s3_htme_bucket = os.getenv("S3_HTME_BUCKET")
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_s3_client()
    dynamodb_client = get_dynamodb_client()
    sns_client = get_sns_client()
    output_prefix = get_output_prefix(args, dynamodb_client, run_time_stamp)
    save_output_location(output_prefix)
    secret_name = (
        secret_name_incremental
        if args.snapshot_type.lower() == SNAPSHOT_TYPE_INCREMENTAL
        else secret_name_full
    )
    secrets_response = retrieve_secrets(args, secret_name)
    secrets_collections = get_collections(secrets_response, args, dynamodb_client)
    keys_map = {}
    start_time = time.perf_counter()
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
        dynamodb_client,
        sns_client,
        output_prefix,
        None,
    )
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", "all_collections", str(total_time))
