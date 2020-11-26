import argparse
import ast
import zlib

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_s3, mock_dynamodb2

import steps
from steps import generate_dataset_from_htme

COMPLETED_STATUS = "Completed"
HASH_KEY = "Correlation_Id"
RANGE_KEY = "Run_Id"
IN_PROGRESS_STATUS = "In Progress"
MOTO_SERVER_URL = "http://127.0.0.1:5000"
DYNAMODB_AUDIT_TABLENAME = "${data_pipeline_metadata}"
DB_CORE_CONTRACT = "db.core.contract"
DB_CORE_ACCOUNTS = "db.core.accounts"
DB_CORE_CONTRACT_FILE_NAME = f"{DB_CORE_CONTRACT}.01002.4040.gz.enc"
DB_CORE_ACCOUNTS_FILE_NAME = f"{DB_CORE_ACCOUNTS}.01002.4040.gz.enc"
S3_PREFIX = "mongo/ucdata"
S3_HTME_BUCKET = "test"
S3_PUBLISH_BUCKET = "target"
SECRETS = "{'collections_all': {'db.core.contract': 'crown'}}"
SECRETS_COLLECTIONS = {DB_CORE_CONTRACT: "crown"}
KEYS_MAP = {"test_ciphertext": "test_key"}
RUN_TIME_STAMP = "2020-10-10_10-10-10"
PUBLISHED_DATABASE_NAME = "test_db"
RUN_ID = 1
CORRELATION_ID = "12345"
AWS_REGION = "eu-west-2"
S3_PREFIX_ADG = "${file_location}/" + f"{RUN_TIME_STAMP}"
ADG_HIVE_TABLES_METADATA_FILE_LOCATION = "${file_location}/adg_output"
ADG_OUTPUT_FILE_KEY = "${file_location}/adg_output/adg_params.csv"


def test_retrieve_secrets(monkeypatch):
    class MockSession:
        class Session:
            def client(self, service_name):
                class Client:
                    def get_secret_value(self, SecretId):
                        return {"SecretBinary": str.encode(SECRETS)}

                return Client()

    monkeypatch.setattr(boto3, "session", MockSession)
    assert generate_dataset_from_htme.retrieve_secrets() == ast.literal_eval(SECRETS)


def test_get_collections():
    secret_dict = ast.literal_eval(SECRETS)
    assert (
        generate_dataset_from_htme.get_collections(secret_dict, mock_args())
        == SECRETS_COLLECTIONS
    )


@mock_s3
def test_get_list_keys_for_prefix(aws_credentials):
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.put_object(
        Body="test",
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
    )

    assert generate_dataset_from_htme.get_list_keys_for_prefix(
        s3_client, S3_HTME_BUCKET, S3_PREFIX
    ) == [f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}"]


def test_group_keys_by_collection():
    keys = [
        f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
        f"{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}",
    ]
    assert generate_dataset_from_htme.group_keys_by_collection(keys) == [
        {f"{DB_CORE_CONTRACT}": [f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}"]},
        {f"{DB_CORE_ACCOUNTS}": [f"{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}"]},
    ]


def test_get_collections_in_secrets():
    list_of_dicts = [
        {f"{DB_CORE_CONTRACT}": [f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}"]},
        {f"{DB_CORE_ACCOUNTS}": [f"{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}"]},
    ]
    expected_list_of_dicts = [
        {f"{DB_CORE_CONTRACT}": [f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}"]}
    ]
    assert (
        generate_dataset_from_htme.get_collections_in_secrets(
            list_of_dicts, SECRETS_COLLECTIONS, mock_args()
        )
        == expected_list_of_dicts
    )


@mock_s3
def test_consolidate_rdd_per_collection_with_one_collection(
    spark, monkeypatch, handle_server, aws_credentials
):
    tbl_name = "core_contract"
    collection_location = "core"
    collection_name = "contract"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f"${{file_location}}/{RUN_TIME_STAMP}/{collection_location}/{collection_name}/part-00000"
    target_object_tag = {"Key": "collection_tag", "Value": "crown"}
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    s3_client.put_object(
        Body=zlib.compress(test_data),
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    monkeypatch.setattr(steps.generate_dataset_from_htme, "add_metric", mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decompress", mock_decompress)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decrypt", mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "call_dks", mock_call_dks)
    monkeypatch.setattr(
        steps.generate_dataset_from_htme, "get_resource", mock_get_dynamodb_resource
    )
    generate_dataset_from_htme.main(
        spark,
        s3_client,
        S3_HTME_BUCKET,
        SECRETS_COLLECTIONS,
        KEYS_MAP,
        RUN_TIME_STAMP,
        S3_PUBLISH_BUCKET,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
        RUN_ID,
        s3_resource
    )
    assert len(s3_client.list_buckets()["Buckets"]) == 2
    assert (
        s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)["Body"]
        .read()
        .decode()
        .strip()
        == test_data.decode()
    )
    assert (
        s3_client.get_object_tagging(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)[
            "TagSet"
        ][0]
        == target_object_tag
    )
    assert tbl_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert (
        CORRELATION_ID
        in s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=ADG_OUTPUT_FILE_KEY)[
            "Body"
        ]
        .read()
        .decode()
    )

    assert (
        S3_PREFIX_ADG
        in s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=ADG_OUTPUT_FILE_KEY)[
            "Body"
        ]
        .read()
        .decode()
    )

def test_consolidate_rdd_per_collection_with_multiple_collections(
    spark, monkeypatch, handle_server, aws_credentials
):
    core_contract_collection_name = "core_contract"
    core_accounts_collection_name = "core_accounts"
    test_data = '{"name":"abcd"}\n{"name":"xyz"}'
    secret_collections = SECRETS_COLLECTIONS
    secret_collections[DB_CORE_ACCOUNTS] = "crown"
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_publish_bucket_for_multiple_collections = f"{S3_PUBLISH_BUCKET}-2"
    s3_client.create_bucket(Bucket=s3_publish_bucket_for_multiple_collections)
    s3_client.put_object(
        Body=zlib.compress(str.encode(test_data)),
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    s3_client.put_object(
        Body=zlib.compress(str.encode(test_data)),
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    monkeypatch.setattr(steps.generate_dataset_from_htme, "add_metric", mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decompress", mock_decompress)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decrypt", mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "call_dks", mock_call_dks)
    monkeypatch.setattr(
        steps.generate_dataset_from_htme, "get_resource", mock_get_dynamodb_resource
    )
    generate_dataset_from_htme.main(
        spark,
        s3_client,
        S3_HTME_BUCKET,
        secret_collections,
        KEYS_MAP,
        RUN_TIME_STAMP,
        s3_publish_bucket_for_multiple_collections,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
        RUN_ID,
        s3_resource
    )
    assert core_contract_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert core_accounts_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


def test_create_hive_on_published(spark, handle_server, aws_credentials):
    json_location = "s3://test/t"
    collection_name = "tabtest"
    all_processed_collections = [(collection_name, json_location)]
    steps.generate_dataset_from_htme.create_hive_tables_on_published(
        spark, all_processed_collections, PUBLISHED_DATABASE_NAME, mock_args(), RUN_ID
    )
    assert generate_dataset_from_htme.get_collection(collection_name) in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


@mock_s3
def test_exception_when_decompression_fails(
    spark, monkeypatch, handle_server, aws_credentials
):
    with pytest.raises(SystemExit):
        s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
        s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
        s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
        s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
        s3_client.put_object(
            Body=zlib.compress(b"test data"),
            Bucket=S3_HTME_BUCKET,
            Key=f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
            Metadata={
                "iv": "123",
                "ciphertext": "test_ciphertext",
                "datakeyencryptionkeyid": "123",
            },
        )
        monkeypatch.setattr(
            steps.generate_dataset_from_htme, "add_metric", mock_add_metric
        )
        monkeypatch.setattr(steps.generate_dataset_from_htme, "decrypt", mock_decrypt)
        monkeypatch.setattr(steps.generate_dataset_from_htme, "call_dks", mock_call_dks)
        monkeypatch.setattr(
            steps.generate_dataset_from_htme, "get_resource", mock_get_dynamodb_resource
        )
        generate_dataset_from_htme.main(
            spark,
            s3_client,
            S3_HTME_BUCKET,
            SECRETS_COLLECTIONS,
            KEYS_MAP,
            RUN_TIME_STAMP,
            S3_PUBLISH_BUCKET,
            PUBLISHED_DATABASE_NAME,
            mock_args(),
            RUN_ID,
            s3_resource
        )


@mock_dynamodb2
def test_log_start_of_batch():
    dynamodb = mock_get_dynamodb_resource("dynamodb")
    assert generate_dataset_from_htme.log_start_of_batch(CORRELATION_ID, dynamodb) == 1
    assert query_audit_table_status(dynamodb) == IN_PROGRESS_STATUS


@mock_dynamodb2
def test_log_start_of_batch_for_multiple_runs():
    dynamodb = mock_get_dynamodb_resource("dynamodb")
    generate_dataset_from_htme.log_start_of_batch(CORRELATION_ID, dynamodb)
    # Ran second time to increment Run_Id by 1 to 2
    assert generate_dataset_from_htme.log_start_of_batch(CORRELATION_ID, dynamodb) == 2
    assert query_audit_table_status(dynamodb) == IN_PROGRESS_STATUS


@mock_dynamodb2
def test_log_end_of_batch():
    dynamodb = mock_get_dynamodb_resource("dynamodb")
    generate_dataset_from_htme.log_end_of_batch(
        CORRELATION_ID, RUN_ID, COMPLETED_STATUS, dynamodb
    )
    assert query_audit_table_status(dynamodb) == COMPLETED_STATUS


def query_audit_table_status(dynamodb):
    table = dynamodb.Table(DYNAMODB_AUDIT_TABLENAME)
    response = table.query(
        KeyConditionExpression=Key(HASH_KEY).eq(CORRELATION_ID), ScanIndexForward=False
    )
    return response["Items"][0]["Status"]


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)


def mock_add_metric(metrics_file, collection_name, value):
    return value


def mock_decrypt(plain_text_key, iv_key, data, args, run_id):
    return data


def mock_args():
    args = argparse.Namespace()
    args.correlation_id = CORRELATION_ID
    args.s3_prefix = S3_PREFIX
    return args


def mock_call_dks(cek, kek, args, run_id):
    return kek


def mock_create_hive_tables_on_published(
    spark, all_processed_collections, published_database_name, args, run_id
):
    return published_database_name


@mock_dynamodb2
def mock_get_dynamodb_resource(service_name):
    dynamodb = boto3.resource(service_name, region_name=AWS_REGION)
    dynamodb.create_table(
        TableName=DYNAMODB_AUDIT_TABLENAME,
        KeySchema=[
            {"AttributeName": HASH_KEY, "KeyType": "HASH"},  # Partition key
            {"AttributeName": RANGE_KEY, "KeyType": "RANGE"},  # Sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": HASH_KEY, "AttributeType": "S"},
            {"AttributeName": RANGE_KEY, "AttributeType": "N"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
    return dynamodb
