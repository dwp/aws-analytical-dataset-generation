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
    s3_resource,
    dynamodb_client,
):
    try:
        keys = get_list_keys_for_prefix(s3_client, s3_htme_bucket, args.s3_prefix)
        list_of_dicts = group_keys_by_collection(keys)
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
        run_time_stamp,
        args.snapshot_type,
        args.export_date,
    )


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
    s3_resource,
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
            itertools.repeat(s3_resource)
        )

    for completed_collection in completed_collections:
        all_processed_collections.append(completed_collection)

    return all_processed_collections


def create_metastore_db(
    spark,
    published_database_name,
    args,
):
    # Check to create database only if the backend is Aurora as Glue database is created through terraform
    if "${hive_metastore_backend}" == "aurora":
        try:
            the_logger.info(
                "Creating metastore db while processing correlation_id %s",
                args.correlation_id,
            )
            verified_database_name = (
                published_database_name
                if args.snapshot_type.lower() == SNAPSHOT_TYPE_FULL
                else f"{published_database_name}_{SNAPSHOT_TYPE_INCREMENTAL}"
            )
            create_db_query = f"CREATE DATABASE IF NOT EXISTS {verified_database_name}"
            spark.sql(create_db_query)

            return verified_database_name
        except BaseException as ex:
            the_logger.error(
                "Error occurred creating hive metastore backend %s",
                repr(ex),
            )
            raise BaseException(ex)


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
    s3_resource,
):
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
        encrypted = read_binary(
            spark, f"s3://{s3_htme_bucket}/{collection_file_key}"
        )
        metadata = get_metadatafor_key(
            collection_file_key, s3_client, s3_htme_bucket
        )
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
    consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
    the_logger.info(
        "Persisting Json of collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
    collection_name_key = get_collection(collection_name)
    collection_name_key = collection_name_key.replace("_", "-")
    file_location = "${file_location}"
    json_location_prefix = f"{file_location}/{args.snapshot_type.lower()}/{run_time_stamp}/{collection_name_key}/"
    json_location = f"s3://{s3_publish_bucket}/{json_location_prefix}"
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
    add_metric(
        "htme_collection_size.csv", collection_name, str(total_collection_size)
    )
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
    adg_json_prefix = (
        f"{file_location}/{args.snapshot_type.lower()}/{run_time_stamp}"
    )
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


def create_hive_table_on_published_for_collection(
    spark,
    collection_name,
    collection_json_location,
    verified_database_name,
    args,
):
    hive_table_name = get_collection(collection_name)
    hive_table_name = hive_table_name.replace("/", "_")
    src_hive_table = verified_database_name + "." + hive_table_name
    the_logger.info(
        "Publishing collection named : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
    )
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
    client = boto3.client("dynamodb", region_name="${aws_default_region}", config=client_config)
    return client


def get_s3_resource():
    return boto3.resource("s3", region_name="${aws_default_region}")


def get_list_keys_for_prefix(s3_client, s3_htme_bucket, s3_prefix):
    the_logger.info(
        "Looking for files to process in bucket : %s with prefix : %s",
        s3_htme_bucket,
        s3_prefix,
    )
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


def get_collections(secrets_response, args):
    try:
        collections = secrets_response["collections_all"]
        collections = {k: v for k, v in collections.items()}
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
    run_time_stamp,
    snapshot_type,
    export_date,
):
    file_location = "${file_location}"

    with open("adg_params.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["correlation_id", "s3_prefix", "snapshot_type", "export_date"])
        writer.writerow(
            [
                correlation_id,
                f"{file_location}/{snapshot_type}/{run_time_stamp}",
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


def save_output_location(args, run_time_stamp):
    file_location = "${file_location}"
    output_location = f"{file_location}/{args.snapshot_type}/{run_time_stamp}"

    with open("/opt/emr/output_location.txt", "wt") as output_location_file:
        output_location_file.write(output_location)


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
    save_output_location(args, run_time_stamp)
    published_database_name = "${published_db}"
    secret_name_full = "${secret_name_full}"
    secret_name_incremental = "${secret_name_incremental}"
    s3_htme_bucket = os.getenv("S3_HTME_BUCKET")
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_s3_client()
    s3_resource = get_s3_resource()
    dynamodb_client = get_dynamodb_client()
    secret_name = (
        secret_name_incremental
        if args.snapshot_type.lower() == SNAPSHOT_TYPE_INCREMENTAL
        else secret_name_full
    )
    secrets_response = retrieve_secrets(args, secret_name)
    secrets_collections = get_collections(secrets_response, args)
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
        s3_resource,
        dynamodb_client,
    )
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    add_metric("processing_times.csv", "all_collections", str(total_time))
