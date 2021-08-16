import argparse
import ast
import zlib
import requests
import time
import json

import boto3
import pytest
from moto import mock_s3, mock_dynamodb2, mock_sns
from datetime import datetime
from pyspark.sql import Row

import steps
from steps import generate_dataset_from_htme

VALUE_KEY = "Value"
NAME_KEY = "Key"
PII_KEY = "pii"
TRUE_VALUE = "true"
DB_KEY = "db"
TABLE_KEY = "table"
SNAPSHOT_TYPE_FULL = "full"
SNS_TOPIC_ARN = "test_arn"
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
@mock_sns
def test_consolidate_rdd_per_collection_with_one_collection_snapshot_type_full(
    spark, monkeypatch, handle_server, aws_credentials
):
    mocked_args = mock_args()
    verify_processed_data(
        mocked_args, monkeypatch, spark, S3_PREFIX_ADG_FULL, ADG_OUTPUT_FILE_KEY_FULL
    )


@mock_s3
@mock_sns
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
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}\n'
    target_object_key = f"${{file_location}}/{mocked_args.snapshot_type}/{RUN_TIME_STAMP}/{collection_location}/{collection_name}/part-00000"
    sns_client = boto3.client("sns", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
        dynamodb_client,
        sns_client,
        s3_resource,
    )
    assert len(s3_client.list_buckets()["Buckets"]) == 2
    assert (
        s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)["Body"]
        .read()
        .decode()
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


@mock_sns
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
    sns_client = boto3.client("sns", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
        dynamodb_client,
        sns_client,
        s3_resource,
    )
    assert core_contract_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert core_accounts_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


@mock_sns
def test_consolidate_rdd_per_collection_with_multiple_collections_where_one_is_empty(
    spark, monkeypatch, handle_server, aws_credentials
):
    core_full_collection_name = "core_full"
    empty_collection_name = "fake_empty"
    test_data = '{"name":"abcd"}\n{"name":"xyz"}'
    secret_collections = {}
    secret_collections["db.core.full"] = {
        PII_KEY: TRUE_VALUE,
        DB_KEY: "core",
        TABLE_KEY: "full",
    }
    secret_collections["db.fake.empty"] = {
        PII_KEY: TRUE_VALUE,
        DB_KEY: "fake",
        TABLE_KEY: "empty",
    }
    sns_client = boto3.client("sns", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_publish_bucket_for_multiple_collections = f"{S3_PUBLISH_BUCKET}-2"
    s3_client.create_bucket(Bucket=s3_publish_bucket_for_multiple_collections)
    s3_client.put_object(
        Body=zlib.compress(str.encode(test_data)),
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/db.core.full.01002.4040.gz.enc",
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
        dynamodb_client,
        sns_client,
        s3_resource,
    )
    assert core_full_collection_name in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]
    assert empty_collection_name not in [
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
    monkeypatch.setattr(steps.generate_dataset_from_htme, "call_dks", mock_call_dks)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "get_metadatafor_key", mock_get_metadatafor_key)




def test_create_hive_table_on_published_for_collection(
    spark, handle_server, aws_credentials, monkeypatch
):
    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
    json_location = "s3://test/t"
    collection_name = "tabtest"
    steps.generate_dataset_from_htme.create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        json_location,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
    )

    monkeypatch.setattr(
        steps.generate_dataset_from_htme, "persist_json", mock_persist_json
    )
    assert generate_dataset_from_htme.get_collection(collection_name) in [
        x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)
    ]


@mock_s3
def test_create_hive_table_on_published_for_audit_log(
    spark, handle_server, aws_credentials, monkeypatch
):
    spark.sql("drop table if exists uc_dw_auditlog.auditlog_managed")
    args = mock_args()
    test_data = '{"first_name":"abcd","last_name":"xyz"}'
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    date_hyphen = args.export_date
    s3_client.put_object(
        Body=str.encode(test_data),
        Bucket=S3_PUBLISH_BUCKET,
        Key=f"data/businessAudit/{date_hyphen}/auditlog.1444209739198.json.gz.enc",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    json_location = f"s3://{S3_PUBLISH_BUCKET}/data/businessAudit/{date_hyphen}/"
    collection_name = "data/businessAudit"
    monkeypatch.setattr(steps.generate_dataset_from_htme, "get_audit_managed_file", mock_get_audit_managed_file)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "get_audit_external_file", mock_get_audit_external_file)
    steps.generate_dataset_from_htme.create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        json_location,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
    )
    steps.generate_dataset_from_htme.create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        json_location,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
    )
    managed_table = 'auditlog_managed'
    managed_table_raw = 'auditlog_raw'
    tables = spark.catalog.listTables('uc_dw_auditlog')
    actual = list(map(lambda table: table.name, tables))
    expected = [managed_table, managed_table_raw]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
    managed_table_result = spark.sql(f"select first_name, last_name, date_str from uc_dw_auditlog.{managed_table}").collect()
    print(managed_table_result)
    expected = [Row(first_name='abcd', last_name='xyz', date_str=date_hyphen), Row(first_name='abcd', last_name='xyz', date_str=date_hyphen)]
    expected_json = json.dumps(expected)
    actual_json = json.dumps(managed_table_result)
    print(expected_json)
    print(actual_json)
    assert len(managed_table_result) == 1

    managed_table_raw_result = spark.sql(f"select * from uc_dw_auditlog.{managed_table_raw}").collect()
    print(managed_table_raw_result)
    expected = [Row(val='{"first_name":"abcd","last_name":"xyz"}', date_str=date_hyphen), Row(val='{"first_name":"abcd","last_name":"xyz"}', date_str=date_hyphen)]
    expected_json = json.dumps(expected)
    actual_json = json.dumps(managed_table_raw_result)
    print(expected_json)
    print(actual_json)
    assert len(expected) == len(managed_table_raw_result)

    auditlog_sec_v_table = 'auditlog_sec_v'
    auditlog_red_v_table = 'auditlog_red_v'
    view_tables = spark.catalog.listTables('uc')
    view_tables_actual = list(map(lambda table: table.name, view_tables))
    view_tables_expected = [auditlog_sec_v_table, auditlog_red_v_table]
    assert len(view_tables_actual) == len(view_tables_expected)
    sec_v_table_result = spark.sql(f"select date_str from uc.{auditlog_sec_v_table}").collect()
    print(sec_v_table_result)
    red_v_table_result = spark.sql(f"select firstname_hash, lastname_hash, date_str from uc.{auditlog_red_v_table}").collect()
    print(red_v_table_result)


@mock_s3
def test_create_hive_table_on_published_for_equality(
    spark, handle_server, aws_credentials, monkeypatch
):
    spark.sql("drop table if exists uc_equality.equality_managed")
    args = mock_args()
    test_data = '{"message":{"type":"abcd","claimantId":"efg","ethnicGroup":"hij","ethnicitySubgroup":"klm","sexualOrientation":"nop","religion":"qrst","maritalStatus":"uvw"}}'
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    date_hyphen = args.export_date
    s3_client.put_object(
        Body=str.encode(test_data),
        Bucket=S3_PUBLISH_BUCKET,
        Key=f"data/equality/{date_hyphen}/equality.1444209739198.json.gz.enc",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    json_location = f"s3://{S3_PUBLISH_BUCKET}/data/equality/{date_hyphen}/"
    collection_name = "data/equality"
    monkeypatch.setattr(steps.generate_dataset_from_htme, "get_equality_managed_file", mock_get_equality_managed_file)
    monkeypatch.setattr(steps.generate_dataset_from_htme, "get_equality_external_file", mock_get_equality_external_file)
    steps.generate_dataset_from_htme.create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        json_location,
        PUBLISHED_DATABASE_NAME,
        mock_args(),
    )
    managed_table = 'equality_managed'
    tables = spark.catalog.listTables('uc_equality')
    actual = list(map(lambda table: table.name, tables))
    expected = [managed_table]
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])
    managed_table_result = spark.sql(f"select claimantid, ethnicGroup, ethnicitySubgroup, sexualOrientation, religion, maritalStatus from uc_equality.{managed_table}").collect()
    print(managed_table_result)
    expected = [Row(type='abcd', claimantid='efg', ethnicGroup='hij', ethnicitySubgroup='klm', sexualOrientation='nop', religion='qrst', maritalStatus='uvw')]
    expected_json = json.dumps(expected)
    actual_json = json.dumps(managed_table_result, default=str)
    print(expected_json)
    print(actual_json)
    assert len(managed_table_result) == 1

@mock_s3
def test_exception_when_decompression_fails(
    spark, monkeypatch, handle_server, aws_credentials
):
    with pytest.raises(BaseException):
        sns_client = boto3.client("sns", region_name="eu-west-2", endpoint_url=MOTO_SERVER_URL)
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
            dynamodb_client,
            sns_client,
            s3_resource,
        )

@mock_dynamodb2
def test_update_adg_status_for_collection():
    expected = "test_status"
    collection_name = "test_collection"

    dynamodb_client = boto3.client("dynamodb", region_name="eu-west-2")
    table_name = "UCExportToCrownStatus"
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

    active = False
    while active == False:
        response = dynamodb_client.describe_table(
            TableName=table_name
        )
        active = (response["Table"]["TableStatus"] == "ACTIVE")

    generate_dataset_from_htme.update_adg_status_for_collection(
        dynamodb_client,
        table_name,
        CORRELATION_ID,
        collection_name,
        expected,
    )

    actual = dynamodb_client.get_item(
        TableName=table_name,
        Key={
            "CorrelationId": {"S": CORRELATION_ID},
            "CollectionName": {"S": collection_name},
        }
    )["Item"]["ADGStatus"]["S"]

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


def mock_get_metadatafor_key(key, s3_client, s3_htme_bucket):
    return {
               "iv": "123",
               "ciphertext": "test_ciphertext",
               "datakeyencryptionkeyid": "123",
           }


def mock_args():
    args = argparse.Namespace()
    args.correlation_id = CORRELATION_ID
    args.s3_prefix = S3_PREFIX
    args.snapshot_type = SNAPSHOT_TYPE_FULL
    args.export_date = EXPORT_DATE
    args.monitoring_topic_arn = SNS_TOPIC_ARN
    return args


def mock_call_dks(cek, kek, args, run_time_stamp):
    return kek


# Mocking because we don't have the compression codec libraries available in test phase
def mock_persist_json(json_location, values):
    values.saveAsTextFile(json_location)

def mock_get_audit_managed_file():
    return open("tests/auditlog_managed_table.sql")

def mock_get_audit_external_file():
    return open("tests/auditlog_external_table.sql")

def mock_get_equality_managed_file():
    return open("tests/equality_managed_table.sql")

def mock_get_equality_external_file():
    return open("tests/equality_external_table.sql")

def mock_get_auditlog_sec_v_file():
    return open("tests/alter_add_part_auditlog_sec_v.sql")

def mock_get_auditlog_sec_v_columns_file():
    return open("tests/auditlog_sec_v_columns.txt")

def mock_get_auditlog_red_v_file():
    return open("tests/alter_add_part_auditlog_red_v.sql")

def mock_get_auditlog_red_v_columns_file():
    return open("tests/auditlog_red_v_columns.txt")


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


@mock_s3
def test_delete_existing_s3_files(aws_credentials):
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.put_object(
        Body="test1",
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}",
    )
    s3_client.put_object(
        Body="test2",
        Bucket=S3_HTME_BUCKET,
        Key=f"{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}",
    )

    keys = generate_dataset_from_htme.get_list_keys_for_prefix(
        s3_client, S3_HTME_BUCKET, S3_PREFIX)

    assert len(keys) == 2

    generate_dataset_from_htme.delete_existing_s3_files(
        S3_HTME_BUCKET, S3_PREFIX, s3_client)

    keys = generate_dataset_from_htme.get_list_keys_for_prefix(
        s3_client, S3_HTME_BUCKET, S3_PREFIX)

    assert len(keys) == 0


@mock_sns
def test_send_sns_message():
    status = "test_status"
    collection_name = "test_collection"
    sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)
    sns_client.create_topic(
        Name="status_topic", Attributes={"DisplayName": "test-topic"}
    )

    topics_json = sns_client.list_topics()
    status_topic_arn = topics_json["Topics"][0]["TopicArn"]

    response = generate_dataset_from_htme.notify_of_collection_failure(
        sns_client,
        status_topic_arn,
        CORRELATION_ID,
        collection_name,
        status,
        SNAPSHOT_TYPE_FULL,
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
