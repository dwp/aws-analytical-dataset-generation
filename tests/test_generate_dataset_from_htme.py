import argparse
import ast
import zlib
import requests
import time

import boto3
import pytest
from moto import mock_s3, mock_dynamodb2
from datetime import datetime

import steps
from steps import generate_dataset_from_htme

VALUE_KEY = "Value"
NAME_KEY = "Key"
PII_KEY = "pii"
TRUE_VALUE = "true"
DB_KEY = "db"
TABLE_KEY = "table"
SNAPSHOT_TYPE_FULL = "full"
SNAPSHOT_TYPE_INCREMENTAL = "incremental"
SNAPSHOT_TYPE_KEY = "snapshot_type"
TAG_SET_FULL = [
    {NAME_KEY: PII_KEY, VALUE_KEY: TRUE_VALUE},
    {NAME_KEY: DB_KEY, VALUE_KEY: "core"},
    {NAME_KEY: TABLE_KEY, VALUE_KEY: "contract"},
    {NAME_KEY: SNAPSHOT_TYPE_KEY, VALUE_KEY: SNAPSHOT_TYPE_FULL},
]
TAG_SET_INCREMENTAL = [
    {NAME_KEY: PII_KEY, VALUE_KEY: TRUE_VALUE},
    {NAME_KEY: DB_KEY, VALUE_KEY: "core"},
    {NAME_KEY: TABLE_KEY, VALUE_KEY: "contract"},
    {NAME_KEY: SNAPSHOT_TYPE_KEY, VALUE_KEY: SNAPSHOT_TYPE_INCREMENTAL},
]
INVALID_SNAPSHOT_TYPE = "abc"
MOCK_LOCALHOST_URL = "http://localhost:1000"
MOTO_SERVER_URL = "http://127.0.0.1:5000"
DB_CORE_CONTRACT = "db.core.contract"
DB_CORE_ACCOUNTS = "db.core.accounts"
DB_CORE_CONTRACT_FILE_NAME = f"{DB_CORE_CONTRACT}.01002.4040.gz.enc"
DB_CORE_ACCOUNTS_FILE_NAME = f"{DB_CORE_ACCOUNTS}.01002.4040.gz.enc"
S3_PREFIX = "mongo/ucdata"
S3_HTME_BUCKET = "test"
S3_PUBLISH_BUCKET = "target"
SECRETS = "{'collections_all': {'db.core.contract': {'pii' : 'true', 'db' : 'core', 'table' : 'contract'}}}"
SECRETS_COLLECTIONS = {
    DB_CORE_CONTRACT: {"pii": "true", "db": "core", "table": "contract"}
}
KEYS_MAP = {"test_ciphertext": "test_key"}
RUN_TIME_STAMP = "2020-10-10_10-10-10"
EXPORT_DATE = "2020-10-10"
PUBLISHED_DATABASE_NAME = "test_db"
CORRELATION_ID = "12345"
AWS_REGION = "eu-west-2"
S3_PREFIX_ADG_FULL = f"${{file_location}}/{SNAPSHOT_TYPE_FULL}/{RUN_TIME_STAMP}"
ADG_OUTPUT_FILE_KEY_FULL = (
    f"${{file_location}}/{SNAPSHOT_TYPE_FULL}/adg_output/adg_params.csv"
)
S3_PREFIX_ADG_INCREMENTAL = (
    f"${{file_location}}/{SNAPSHOT_TYPE_INCREMENTAL}/{RUN_TIME_STAMP}"
)
ADG_OUTPUT_FILE_KEY_INCREMENTAL = (
    f"${{file_location}}/{SNAPSHOT_TYPE_INCREMENTAL}/adg_output/adg_params.csv"
)


def test_retrieve_secrets(monkeypatch):
    class MockSession:
        class Session:
            def client(self, service_name):
                class Client:
                    def get_secret_value(self, SecretId):
                        return {"SecretBinary": str.encode(SECRETS)}

                return Client()

    monkeypatch.setattr(boto3, "session", MockSession)
    assert generate_dataset_from_htme.retrieve_secrets(
        mock_args(), SNAPSHOT_TYPE_FULL
    ) == ast.literal_eval(SECRETS)


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
def test_consolidate_rdd_per_collection_with_one_collection_snapshot_type_full(
    spark, monkeypatch, handle_server, aws_credentials
):
    mocked_args = mock_args()
    verify_processed_data(
        mocked_args, monkeypatch, spark, S3_PREFIX_ADG_FULL, ADG_OUTPUT_FILE_KEY_FULL
    )


@mock_s3
def test_consolidate_rdd_per_collection_with_one_collection_snapshot_type_incremental(
    spark, monkeypatch, handle_server, aws_credentials
):
    mocked_args = mock_args()
    mocked_args.snapshot_type = SNAPSHOT_TYPE_INCREMENTAL
    verify_processed_data(
        mocked_args,
        monkeypatch,
        spark,
        S3_PREFIX_ADG_INCREMENTAL,
        ADG_OUTPUT_FILE_KEY_INCREMENTAL,
    )


def verify_processed_data(
    mocked_args, monkeypatch, spark, s3_prefix_adg, adg_output_key
):
    tag_set = (
        TAG_SET_FULL
        if mocked_args.snapshot_type == SNAPSHOT_TYPE_FULL
        else TAG_SET_INCREMENTAL
    )
    tbl_name = "core_contract"
    collection_location = "core"
    collection_name = "contract"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f"${{file_location}}/{mocked_args.snapshot_type}/{RUN_TIME_STAMP}/{collection_location}/{collection_name}/part-00000"
    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
    monkeypatch_with_mocks(monkeypatch)
    generate_dataset_from_htme.main(
        spark,
        s3_client,
        S3_HTME_BUCKET,
        SECRETS_COLLECTIONS,
        KEYS_MAP,
        RUN_TIME_STAMP,
        S3_PUBLISH_BUCKET,
        PUBLISHED_DATABASE_NAME,
        mocked_args,
        s3_resource,
        dynamodb_client,
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
        ]
        == tag_set
    )
    assert tbl_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert (
        CORRELATION_ID
        in s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=adg_output_key)["Body"]
        .read()
        .decode()
    )
    assert (
        s3_prefix_adg
        in s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=adg_output_key)["Body"]
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
    secret_collections[DB_CORE_ACCOUNTS] = {
        PII_KEY: TRUE_VALUE,
        DB_KEY: "core",
        TABLE_KEY: "accounts",
    }
    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
    monkeypatch_with_mocks(monkeypatch)
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
        s3_resource,
        dynamodb_client,
    )
    assert core_contract_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert core_accounts_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


def monkeypatch_with_mocks(monkeypatch):
    monkeypatch.setattr(steps.generate_dataset_from_htme, "add_metric", mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decompress", mock_decompress)
    monkeypatch.setattr(
        steps.generate_dataset_from_htme, "persist_json", mock_persist_json
    )
    monkeypatch.setattr(steps.generate_dataset_from_htme, "decrypt", mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "call_dks", mock_call_dks)


def test_create_hive_on_published_for_full(
    spark, handle_server, aws_credentials, monkeypatch
):
    json_location = "s3://test/t"
    collection_name = "tabtest"
    all_processed_collections = [(collection_name, json_location)]
    steps.generate_dataset_from_htme.create_hive_tables_on_published(
        spark,
        all_processed_collections,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
        RUN_TIME_STAMP,
    )

    monkeypatch.setattr(
        steps.generate_dataset_from_htme, "persist_json", mock_persist_json
    )
    assert generate_dataset_from_htme.get_collection(collection_name) in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


@mock_s3
def test_exception_when_decompression_fails(
    spark, monkeypatch, handle_server, aws_credentials
):
    with pytest.raises(BaseException):
        dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
            s3_resource,
            dynamodb_client,
        )

@mock_dynamodb2
def test_update_adg_status_for_collection(aws_credentials):
    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
    table_name = "UCExportToCrownStatus"
    expected = "test_status"
    collection_name = "test_collection"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'CorrelationId', 'KeyType': 'HASH'},
            {'AttributeName': 'CollectionName', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'CorrelationId', 'AttributeType': 'S'},
            {'AttributeName': 'CollectionName', 'AttributeType': 'S'}
        ]
    )

    generate_dataset_from_htme.update_adg_status_for_collection(
        dynamodb_client,
        table_name,
        CORRELATION_ID,
        collection_name,
        expected,
    )

    actual = dynamodb_client.get_item(
        TableName='UCExportToCrownStatus',
        Key={
            "CorrelationId": {"S": CORRELATION_ID},
            "CollectionName": {"S": collection_name},
        },
    )

    assert expected == actual


def test_get_tags():
    tag_value = SECRETS_COLLECTIONS[DB_CORE_CONTRACT]
    assert (
        generate_dataset_from_htme.get_tags(tag_value, SNAPSHOT_TYPE_FULL)
        == TAG_SET_FULL
    )


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)


def mock_add_metric(metrics_file, collection_name, value):
    return value


def mock_decrypt(plain_text_key, iv_key, data, args, run_time_stamp):
    return data


def mock_args():
    args = argparse.Namespace()
    args.correlation_id = CORRELATION_ID
    args.s3_prefix = S3_PREFIX
    args.snapshot_type = SNAPSHOT_TYPE_FULL
    args.export_date = EXPORT_DATE
    return args


def mock_call_dks(cek, kek, args, run_time_stamp):
    return kek


def mock_create_hive_tables_on_published(
    spark, all_processed_collections, published_database_name, args
):
    return published_database_name


# Mocking because we don't have the compression codec libraries available in test phase
def mock_persist_json(json_location, values):
    values.saveAsTextFile(json_location)


def test_retry_requests_with_no_retries():
    start_time = time.perf_counter()
    with pytest.raises(requests.exceptions.ConnectionError):
        generate_dataset_from_htme.retry_requests(retries=0).post(MOCK_LOCALHOST_URL)
    end_time = time.perf_counter()
    assert round(end_time - start_time) == 0


def test_retry_requests_with_2_retries():
    start_time = time.perf_counter()
    with pytest.raises(requests.exceptions.ConnectionError):
        generate_dataset_from_htme.retry_requests(retries=2).post(MOCK_LOCALHOST_URL)
    end_time = time.perf_counter()
    assert round(end_time - start_time) == 2


def test_retry_requests_with_3_retries():
    start_time = time.perf_counter()
    with pytest.raises(requests.exceptions.ConnectionError):
        generate_dataset_from_htme.retry_requests(retries=3).post(MOCK_LOCALHOST_URL)
    end_time = time.perf_counter()
    assert round(end_time - start_time) == 6


def test_validate_required_args_with_missing_args():
    args = argparse.Namespace()
    with pytest.raises(argparse.ArgumentError) as argument_error:
        generate_dataset_from_htme.validate_required_args(args)
    assert (
        str(argument_error.value)
        == "ArgumentError: The following required arguments are missing: correlation_id, s3_prefix, snapshot_type"
    )


def test_validate_required_args_with_invalid_values_for_snapshot_type():
    args = argparse.Namespace()
    args.correlation_id = CORRELATION_ID
    args.s3_prefix = S3_PREFIX
    args.export_date = EXPORT_DATE
    args.snapshot_type = INVALID_SNAPSHOT_TYPE
    with pytest.raises(argparse.ArgumentError) as argument_error:
        generate_dataset_from_htme.validate_required_args(args)
    assert (
        str(argument_error.value)
        == "ArgumentError: Valid values for snapshot_type are: full, incremental"
    )
