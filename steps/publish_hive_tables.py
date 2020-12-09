import concurrent.futures
import itertools
import os
import sys

import boto3
from pyspark.sql import SparkSession

from steps.logger import setup_logging

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def get_collection(collection_name):
    return (
        collection_name.replace("db.", "", 1)
        .replace(".", "_")
        .replace("-", "_")
        .lower()
    )


def main(spark, s3_client, s3_publish_bucket, published_database_name):
    adg_hive_metadata_file_location = "${file_location}/adg_output"
    adg_hive_metadata_file_name = "analytical-dataset-hive-tables-metadata.csv"
    adg_hive_tables_metadata_object_key = (
        f"{adg_hive_metadata_file_location}/{adg_hive_metadata_file_name}"
    )
    the_logger.info(
        "Getting Hive tables metadata file from S3"
    )
    hive_tables_metadata = (
        s3_client.get_object(
            Bucket=s3_publish_bucket, Key=adg_hive_tables_metadata_object_key
        )["Body"]
        .read()
        .decode()
        .strip()
        .split("\r\n")
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(
            create_hive_tables_on_published,
            hive_tables_metadata,
            itertools.repeat(spark),
            itertools.repeat(published_database_name),
        )


def create_hive_tables_on_published(
    hive_tables_metadata, spark, published_database_name
):
    """
    Create CSV with all the collections names and their locations and save it to S3 bucket to be picked up by PDM
    for publishing Hive tables
    """
    try:
        # Check to create database only if the backend is Aurora as Glue database is created through terraform
        if "${hive_metastore_backend}" == "aurora":
            the_logger.info(
                "Creating metastore db while processing"
            )
            create_db_query = f"CREATE DATABASE IF NOT EXISTS {published_database_name}"
            spark.sql(create_db_query)
        (collection_name, collection_json_location) = hive_tables_metadata.split(",")
        hive_table_name = get_collection(collection_name)
        src_hive_table = published_database_name + "." + hive_table_name
        the_logger.info("Creating Hive table for : %s ", src_hive_table)
        src_hive_drop_query = f"DROP TABLE IF EXISTS {src_hive_table}"
        src_hive_create_query = f"""CREATE EXTERNAL TABLE IF NOT EXISTS {src_hive_table}(val STRING)  
                STORED AS TEXTFILE LOCATION "{collection_json_location}" """
        src_hive_analyse_query = (
            f"""ANALYZE TABLE {src_hive_table} COMPUTE STATISTICS"""
        )
        spark.sql(src_hive_drop_query)
        spark.sql(src_hive_create_query)
        the_logger.info("Analyze Hive table for : %s ", src_hive_table)
        spark.sql(src_hive_analyse_query)
    except BaseException as ex:
        the_logger.error(
            "Problem with creating Hive tables %s", str(ex)
        )
        sys.exit(-1)


def get_client(service_name):
    client = boto3.client(service_name)
    return client


def get_spark_session():
    spark_session = (
        SparkSession.builder.master("yarn")
        .config("spark.metrics.namespace", "adg")
        .config("spark.sql.catalogImplementation", "hive")
        .appName("ADG-Publish-Hive-Tables")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark_session.conf.set("spark.scheduler.mode", "FAIR")
    return spark_session


if __name__ == "__main__":
    spark = get_spark_session()
    published_database_name = "${published_db}"
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    s3_client = get_client("s3")
    main(spark, s3_client, s3_publish_bucket, published_database_name)
