import boto3
from moto import mock_s3

from steps import publish_hive_tables

ADG_HIVE_TABLES_METADATA_FILE_LOCATION = "${file_location}/adg_output"
ADG_OUTPUT_FILE_KEY = "${file_location}/adg_output/adg_params.csv"
ADG_HIVE_TABLES_METADATA_FILE_NAME = "analytical-dataset-hive-tables-metadata.csv"
MOTO_SERVER_URL = "http://127.0.0.1:5000"
S3_PUBLISH_BUCKET = "target"
DB_CORE_CONTRACT = "core_contract"
DB_CORE_ACCOUNTS = "core_accounts"
PUBLISHED_DATABASE_NAME = "test_db"
COLLECTION_NAME = "db.core.contract"


@mock_s3
def test_main(spark, handle_server):
    adg_hive_tables_metadata_object_key = (
        f"{ADG_HIVE_TABLES_METADATA_FILE_LOCATION}/{ADG_HIVE_TABLES_METADATA_FILE_NAME}"
    )
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)

    with open(f"./data/{ADG_HIVE_TABLES_METADATA_FILE_NAME}", "rb") as fin:
        s3_client.upload_fileobj(
            fin, S3_PUBLISH_BUCKET, adg_hive_tables_metadata_object_key
        )
    publish_hive_tables.main(
        spark, s3_client, S3_PUBLISH_BUCKET, PUBLISHED_DATABASE_NAME
    )
    assert DB_CORE_CONTRACT in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert DB_CORE_ACCOUNTS in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


def test_get_collection():
    assert DB_CORE_CONTRACT == publish_hive_tables.get_collection(COLLECTION_NAME)
