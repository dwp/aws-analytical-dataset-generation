import argparse
import itertools
import os
import sys
import concurrent.futures

import boto3
import botocore

from pyspark.sql import SparkSession


def main(
        spark,
        s3_client,
        s3_historical_audit_bucket,
        keys_map,
        s3_publish_bucket,
        published_database_name,
        args,
        s3_resource=None,
):
    try:
        keys = get_all_years_for_historic_audit(s3_client, s3_historical_audit_bucket, args.s3_prefix)
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
            keys,
            s3_client,
            s3_historical_audit_bucket,
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


def process_collections_threaded(
        spark,
        verified_database_name,
        args,
        keys,
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
            keys,
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

    year  = key.split('/')[-2]
    keys = get_list_keys_for_prefix(s3_client, s3_historical_audit_bucket, prefix)

    try:
        collection_json_location = consolidate_rdd_per_collection(
            year,
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
            "Error occurred processing collection named %s for correlation id: %s %s",
            collection_name,
            args.correlation_id,
            repr(ex),
        )
        raise CollectionProcessingException(ex)

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
        raise CollectionPublishingException(ex)

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
    if hive_table_name == "data_businessAudit":
        auditlog_managed_table_sql_file = open("/var/ci/auditlog_managed_table.sql")
        auditlog_managed_table_sql_content = (
            auditlog_managed_table_sql_file.read().replace(
                "#{hivevar:auditlog_database}", verified_database_name
            )
        )
        spark.sql(auditlog_managed_table_sql_content)

        auditlog_external_table_sql_file = open("/var/ci/auditlog_external_table.sql")
        date_hyphen = datetime.today().strftime("%Y-%m-%d")
        date_underscore = date_hyphen.replace("-", "_")
        queries = (
            auditlog_external_table_sql_file.read()
                .replace("#{hivevar:auditlog_database}", verified_database_name)
                .replace("#{hivevar:date_underscore}", date_underscore)
                .replace("#{hivevar:date_hyphen}", date_hyphen)
                .replace("#{hivevar:serde}", "org.openx.data.jsonserde.JsonSerDe")
                .replace("#{hivevar:data_location}", collection_json_location)
        )
        split_queries = queries.split(";", 3)
        print(list(map(lambda query: spark.sql(query), split_queries)))
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
        "Processing collection : %s for correlation id : %s",
        collection_name,
    )
    start_time = time.perf_counter()
    rdd_list = []
    total_collection_size = 0
    for collection_file_key in collection_files_keys:
        encrypted = read_binary(spark, f"s3://{s3_htme_bucket}/{collection_file_key}")
        metadata = get_metadatafor_key(collection_file_key, s3_client, s3_htme_bucket)
        total_collection_size += get_filesize(
            s3_client, s3_historical_audit_bucket, collection_file_key
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
    )
    file_location = "${file_location}"
    json_location_prefix = f"{file_location}/{collection_name_key}/"
    json_location = f"s3://{s3_publish_bucket}/{json_location_prefix}"
    delete_existing_audit_files(s3_publish_bucket, json_location_prefix, s3_client)

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
    the_logger.info(
        "Created Hive tables of collection : %s for correlation id : %s",
        collection_name,
    )
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    the_logger.info(
        "Completed Processing of collection : %s for correlation id : %s",
        collection_name,
        args.correlation_id,
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
    required_args = [ARG_S3_PREFIX]
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

def get_parameters():
    """Define and parse command line args."""
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job for historical business audit"
    )
    # Parse command line inputs and set defaults
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    parser.add_argument("--snapshot_type", default="historical_business_audit")
    args, unrecognized_args = parser.parse_known_args()

    if len(unrecognized_args) > 0:
        the_logger.warning(
            "Unrecognized args %s found for the correlation id %s",
            unrecognized_args,
            args.correlation_id,
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


if __name__ == "__main__":
    args = get_parameters()
    the_logger.info(
        "Processing spark job for correlation id : %s, export date : %s, snapshot_type : %s and s3_prefix : %s",
        args.s3_prefix,
    )
spark = get_spark_session(args)
s3_historical_audit_bucket = os.getenv("S3_HISTORICAL_AUDIT_BUCKET")
s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
s3_client = get_s3_client()
published_database_name = "${published_db}"
keys_map = {}
main(
    spark,
    s3_client,
    s3_historical_audit_bucket,
    keys_map,
    s3_publish_bucket,
    published_database_name,
    args,
)


