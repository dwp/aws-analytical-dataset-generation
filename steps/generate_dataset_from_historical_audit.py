import argparse
import base64
import itertools
import os
import sys
import time
import zlib
import concurrent.futures
import urllib.request
from datetime import datetime, timedelta
import boto3
import botocore
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from Crypto.Cipher import AES

from pyspark.sql import SparkSession
from steps.logger import setup_logging
from steps.resume_step import should_skip_step
from datetime import date, timedelta

SNAPSHOT_TYPE_KEY = "snapshot_type"
VALUE_KEY = "Value"
KEY_KEY = "Key"
DEFAULT_REGION = "${aws_default_region}"
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

def main(
        spark,
        s3_client,
        s3_historical_audit_bucket,
        keys_map,
        s3_publish_bucket,
        published_database_name,
        args,
        start_date,
        end_date,
        s3_resource=None,
):
    try:
        # prefixes = get_all_years_for_historic_audit(s3_client, s3_historical_audit_bucket, args.s3_prefix)
        prefixes = get_prefixes_for_selected_dates(s3_historical_audit_bucket, args.s3_prefix, start_date, end_date)
        process_collections_threaded(
            spark,
            '',
            args,
            prefixes,
            s3_client,
            s3_historical_audit_bucket,
            keys_map,
            s3_publish_bucket,
            s3_resource,
        )
    except CollectionException as ex:
        the_logger.error(
            "Some error occurred %s ",
            repr(ex),
        )
        # raising exception is not working with YARN so need to send an exit code(-1) for it to fail the job
        sys.exit(-1)


def process_collections_threaded(
        spark,
        verified_database_name,
        args,
        prefixes,
        s3_client,
        s3_historical_audit_bucket,
        keys_map,
        s3_publish_bucket,
        s3_resource=None,
):
    all_processed_collections = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        completed_collections = executor.map(
            process_collection,
            itertools.repeat(spark),
            itertools.repeat(verified_database_name),
            itertools.repeat(args),
            prefixes,
            itertools.repeat(s3_client),
            itertools.repeat(s3_historical_audit_bucket),
            itertools.repeat(keys_map),
            itertools.repeat(s3_publish_bucket),
            itertools.repeat(s3_resource),
        )

    for completed_collection in completed_collections:
        all_processed_collections.append(completed_collection)

    return all_processed_collections


def process_collection(
        spark,
        verified_database_name,
        args,
        prefix,
        s3_client,
        s3_historical_audit_bucket,
        keys_map,
        s3_publish_bucket,
        s3_resource=None,
):
    if s3_resource is None:
        s3_resource = get_s3_resource()

    day  = prefix.split('/')[-2]
    keys = get_list_keys_for_prefix(s3_client, s3_historical_audit_bucket, prefix)

    the_logger.info(
            "Processing for the day : %s keys : %s",
            day,
            keys,
        )

    try:
        collection_json_location = consolidate_rdd_per_collection(
            day,
            keys,
            s3_client,
            s3_historical_audit_bucket,
            spark,
            keys_map,
            s3_publish_bucket,
            args,
            s3_resource,
        )
    except Exception as ex:
        the_logger.error(
            "Error occurred processing collection named %s: %s",
            day,
            repr(ex),
        )
        raise CollectionProcessingException(ex)

    try:
        create_hive_table_on_published_for_collection(
            spark,
            day,
            collection_json_location,
            args,
        )
    except Exception as ex:
        the_logger.error(
            "Error occurred publishing collection named %s : %s",
            day,
            repr(ex),
        )
        raise CollectionPublishingException(ex)

def create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        collection_json_location,
        args,
):
    verified_database_name_for_audit = 'uc_dw_auditlog'
    date_hyphen = collection_name
    date_underscore = date_hyphen.replace("-", "_")
    the_logger.info(
        "Publishing collection named : %s",
        collection_name,
    )
    create_db_query = f"CREATE DATABASE IF NOT EXISTS {verified_database_name_for_audit}"
    spark.sql(create_db_query)

    create_audit_log_raw_managed_table(spark, verified_database_name_for_audit, date_hyphen, collection_json_location)

    auditlog_managed_table_sql_file = get_audit_managed_file()
    auditlog_managed_table_sql_content = (
        auditlog_managed_table_sql_file.read().replace(
            "#{hivevar:auditlog_database}", verified_database_name_for_audit
        )
    )
    spark.sql(auditlog_managed_table_sql_content)

    auditlog_external_table_sql_file = get_audit_external_file()
    queries = (
        auditlog_external_table_sql_file.read()
            .replace("#{hivevar:auditlog_database}", verified_database_name_for_audit)
            .replace("#{hivevar:date_underscore}", date_underscore)
            .replace("#{hivevar:date_hyphen}", date_hyphen)
            .replace("#{hivevar:serde}", "org.openx.data.jsonserde.JsonSerDe")
            .replace("#{hivevar:data_location}", collection_json_location)
    )
    split_queries = queries.split(";", 4)
    print(list(map(lambda query: spark.sql(query), split_queries)))
    return collection_name


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
        src_externl_hive_drop_query = f"""DROP TABLE IF EXISTS {src_external_hive_table}"""

        spark.sql(src_external_hive_create_query)
        spark.sql(src_external_hive_alter_query)
        spark.sql(src_external_hive_insert_query)
        spark.sql(src_externl_hive_drop_query)


def get_audit_managed_file():
    return open("/var/ci/auditlog_managed_table.sql")

def get_audit_external_file():
    return open("/var/ci/auditlog_external_table.sql")

def consolidate_rdd_per_collection(
        collection_name,
        collection_files_keys,
        s3_client,
        s3_historical_audit_bucket,
        spark,
        keys_map,
        s3_publish_bucket,
        args,
        s3_resource,
):
    the_logger.info(
        "Processing collection : %s",
        collection_name,
    )
    start_time = time.perf_counter()
    rdd_list = []
    for collection_file_key in collection_files_keys:
        key1 = f"s3://{s3_historical_audit_bucket}/{collection_file_key}"
        encrypted = read_binary(spark, key1)
        metadata = get_metadatafor_key(collection_file_key, s3_client, s3_historical_audit_bucket)
        ciphertext = metadata["ciphertext"]
        datakeyencryptionkeyid = metadata["datakeyencryptionkeyid"]
        iv = metadata["iv"]
        plain_text_key = get_plaintext_key_calling_dks(
            ciphertext, datakeyencryptionkeyid, keys_map, args
        )
        decrypted = encrypted.mapValues(
            lambda val, plain_text_key=plain_text_key, iv=iv: decrypt(
                plain_text_key, iv, val, args
            )
        )
        decompressed = decrypted.mapValues(decompress)
        decoded = decompressed.mapValues(decode)
        rdd_list.append(decoded)
    consolidated_rdd = spark.sparkContext.union(rdd_list)
    consolidated_rdd_mapped = consolidated_rdd.map(lambda x: x[1])
    the_logger.info(
        "Persisting Json of collection : %s",
        collection_name,
    )
    file_location = "${file_location}"
    json_location_prefix = f"{file_location}/data/businessAudit/{collection_name}"
    json_location = f"s3://{s3_publish_bucket}/{json_location_prefix}"
    delete_existing_audit_files(s3_publish_bucket, json_location_prefix, s3_client)

    persist_json(json_location, consolidated_rdd_mapped)
    tag_value = {"pii": "true", "db": "data", "table": "businessAudit"}
    tag_objects(
        json_location_prefix,
        tag_value,
        s3_client,
        s3_publish_bucket,
        args.snapshot_type,
    )
    the_logger.info(
        "Applying Tags for prefix : %s",
        json_location_prefix,
    )
    the_logger.info(
        "Created Hive tables of collection : %s",
        collection_name,
    )
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    the_logger.info(
        "Completed Processing of collection : %s",
        collection_name,
    )
    return json_location

def persist_json(json_location, values):
    values.saveAsTextFile(
        json_location, compressionCodecClass="com.hadoop.compression.lzo.LzopCodec"
    )

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

def decode(txt):
    decoded =  txt.decode("utf-8")
    if "\n" == decoded[-1]:
        stripped_last_new_line_character = decoded[:-1]
        return stripped_last_new_line_character
    return decoded

def delete_existing_audit_files(s3_bucket, s3_prefix, s3_client):
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


def get_metadatafor_key(key, s3_client, s3_htme_bucket):
    instance_id = (
        urllib.request.urlopen("http://169.254.169.254/latest/meta-data/instance-id")
            .read()
            .decode()
    )
    the_logger.info("Instance id making boto3 get_object calls: %s ", instance_id)
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

def get_s3_resource():
    session = boto3.session.Session()
    return session.resource("s3", region_name=DEFAULT_REGION)

def get_prefixes_for_selected_dates(s3_bucket, s3_prefix, start_date, end_date):
    prefixes = []
    the_logger.info(
            "Looking for prefixes for dates between : %s and : %s",
            start_date,
            end_date,
        )
    sdate = datetime.strptime(start_date, '%Y-%m-%d').date()  # start date
    edate = datetime.strptime(end_date, '%Y-%m-%d').date() # end date
    delta = edate - sdate       # as timedelta
    for i in range(delta.days + 1):
        day = sdate + timedelta(days=i)
        prefix = f'{s3_prefix}{day}/'
        prefixes.append(prefix)
    return prefixes


def get_all_years_for_historic_audit(s3_client, s3_bucket, s3_prefix):
    the_logger.info(
        "Looking for files to process in bucket : %s with prefix : %s",
        s3_bucket,
        s3_prefix,
    )
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_bucket, Prefix=s3_prefix, Delimiter='/')
    for page in pages:
        for content in  page.get('CommonPrefixes', []):
            keys.append(content.get('Prefix'))
    return keys


def validate_required_args(args):
    required_args = ['s3_prefix', 'start_date', 'end_date']
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


def get_parameters():
    """Define and parse command line args."""
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job for historical business audit"
    )
    # Parse command line inputs and set defaults
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    parser.add_argument("--snapshot_type", default="historical_business_audit")
    parser.add_argument("--start_date", default="2014-11-25")
    parser.add_argument("--end_date", default='2014-11-25')
    args, unrecognized_args = parser.parse_known_args()

    if len(unrecognized_args) > 0:
        the_logger.warning(
            "Unrecognized args %s found",
            unrecognized_args,
        )

    validate_required_args(args)

    return args


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


def get_s3_client():
    client_config = botocore.config.Config(
        max_pool_connections=100, retries={"max_attempts": 10, "mode": "standard"}
    )
    client = boto3.client("s3", config=client_config)
    return client

def decompress(compressed_text):
    return zlib.decompress(compressed_text)

def decrypt(plain_text_key, iv_key, data, args):
    try:
        iv_int = base64.b64decode(iv_key)
        aes = AES.new(base64.b64decode(plain_text_key), AES.MODE_EAX, nonce=iv_int)
        decrypted = aes.decrypt(data)
    except BaseException as ex:
        the_logger.error(
            "Problem decrypting data %s",
            repr(ex),
        )
        sys.exit(-1)
    return decrypted


def get_collection(collection_name):
    return collection_name.replace("db.", "", 1).replace(".", "/").replace("-", "_")

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

def call_dks(cek, kek, args):
    try:
        url = "${url}"
        params = {"keyId": kek, "correlationId": ''}
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
            "Problem calling DKS %s",
            repr(ex),
        )
        sys.exit(-1)
    return content["plaintextDataKey"]

def read_binary(spark, file_path):
    return spark.sparkContext.binaryFiles(file_path)

def get_plaintext_key_calling_dks(
    encryptedkey, keyencryptionkeyid, keys_map, args
):
    if keys_map.get(encryptedkey):
        key = keys_map[encryptedkey]
    else:
        key = call_dks(encryptedkey, keyencryptionkeyid, args)
        keys_map[encryptedkey] = key
    return key

def exit_if_skipping_step():
    if should_skip_step(the_logger, "spark-submit"):
        the_logger.info("Step needs to be skipped so will exit without error")
        sys.exit(0)

if __name__ == "__main__":
    args = get_parameters()
    the_logger.info(
        "Processing spark job for s3_prefix : %s starting from %s to %s",
        args.s3_prefix,
        args.start_date,
        args.end_date
    )
    the_logger.info("Checking if step should be skipped")
    exit_if_skipping_step()

    spark = get_spark_session(args)

    published_database_name = "${published_db}"
    s3_historical_audit_bucket = os.getenv("S3_HISTORICAL_AUDIT_BUCKET")
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_s3_client()
    keys_map = {}
    main(
        spark,
        s3_client,
        s3_historical_audit_bucket,
        keys_map,
        s3_publish_bucket,
        published_database_name,
        args,
        args.start_date,
        args.end_date
    )


