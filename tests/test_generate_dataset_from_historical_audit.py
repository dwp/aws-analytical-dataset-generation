import argparse
import ast
import zlib
import requests
import time

import boto3
import pytest
from moto import mock_s3, mock_dynamodb2, mock_sns
from datetime import datetime
from pyspark.sql import Row
import json

import steps
from steps import generate_dataset_from_historical_audit

VALUE_KEY = "Value"
NAME_KEY = "Key"
PII_KEY = "pii"
TRUE_VALUE = "true"
DB_KEY = "db"
TABLE_KEY = "table"
SNAPSHOT_TYPE_HISTORICAL_BUSINESS_AUDIT = "historical_business_audit"
SNS_TOPIC_ARN = "test_arn"
SNAPSHOT_TYPE_INCREMENTAL = "incremental"
SNAPSHOT_TYPE_KEY = "snapshot_type"
TAG_SET_HISTORICAL_BUSINESS_AUDIT = [
    {NAME_KEY: PII_KEY, VALUE_KEY: TRUE_VALUE},
    {NAME_KEY: DB_KEY, VALUE_KEY: "data"},
    {NAME_KEY: TABLE_KEY, VALUE_KEY: "businessAudit"},
    {NAME_KEY: SNAPSHOT_TYPE_KEY, VALUE_KEY: SNAPSHOT_TYPE_HISTORICAL_BUSINESS_AUDIT},
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
DATA_BUSINESS_AUDIT = "auditlog"
DB_CORE_CONTRACT = "db.core.contract"
DB_CORE_ACCOUNTS = "db.core.accounts"
DB_CORE_CONTRACT_FILE_NAME = f"{DB_CORE_CONTRACT}.01002.4040.gz.enc"
DB_CORE_ACCOUNTS_FILE_NAME = f"{DB_CORE_ACCOUNTS}.01002.4040.gz.enc"
DATA_BUSINESS_AUDIT_FILE_NAME = f"{DATA_BUSINESS_AUDIT}.1444209739198.json.gz.enc"
S3_PREFIX = "auditlog"
S3_HTME_BUCKET = "test"
S3_HISTORICAL_BUSINESS_AUDIT_BUCKET = "test"
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
S3_PREFIX_BUSINESS_AUDIT = f"${{file_location}}/data/businessAudit"

@mock_s3
def test_consolidate_rdd_per_collection_with_one_collection_snapshot_type_full(
    spark, monkeypatch, handle_server, aws_credentials
):
    mocked_args = mock_args()
    verify_processed_data(
        mocked_args, monkeypatch, spark)

def verify_processed_data(
    mocked_args, monkeypatch, spark):
    tag_set = (
        TAG_SET_HISTORICAL_BUSINESS_AUDIT
    )
    tbl_name = "businessAudit"
    collection_location = "data"
    collection_name = "businessAudit"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f"${{file_location}}/{collection_location}/{collection_name}/2021-07-02/part-00000"
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
    historical_business_audit_bucket = s3_client.create_bucket(Bucket=S3_HISTORICAL_BUSINESS_AUDIT_BUCKET)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    s3_client.put_object(
        Body=zlib.compress(test_data),
        Bucket=S3_HISTORICAL_BUSINESS_AUDIT_BUCKET,
        Key=f"{S3_PREFIX}/2021-07-02/{DATA_BUSINESS_AUDIT_FILE_NAME}",
        Metadata={
            "iv": "123",
            "ciphertext": "test_ciphertext",
            "datakeyencryptionkeyid": "123",
        },
    )
    for key in s3_client.list_objects(Bucket=S3_HISTORICAL_BUSINESS_AUDIT_BUCKET, Prefix=f'{S3_PREFIX}/2021-07-02/')['Contents']:
        print(f'keyssss are {key["Key"]}')
    monkeypatch_with_mocks(monkeypatch)
    generate_dataset_from_historical_audit.main(
        spark,
        s3_client,
        S3_HISTORICAL_BUSINESS_AUDIT_BUCKET,
        KEYS_MAP,
        S3_PUBLISH_BUCKET,
        PUBLISHED_DATABASE_NAME,
        mocked_args,
        '2021-07-02',
        '2021-07-02',
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
        ]
        == tag_set
    )

@mock_s3
def test_create_hive_table_on_published_for_audit_log(
    spark, handle_server, aws_credentials, monkeypatch
):
    spark.sql("drop table uc_dw_auditlog.auditlog_managed")
    test_data = '{"first_name":"abcd","last_name":"xyz"}'
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    date_hyphen = datetime.today().strftime("%Y-%m-%d")
    date_underscore = date_hyphen.replace("-", "_")
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
    collection_name = date_hyphen
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "get_audit_managed_file", mock_get_audit_managed_file)
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "get_audit_external_file", mock_get_audit_external_file)
    steps.generate_dataset_from_historical_audit.create_hive_table_on_published_for_collection(
        spark,
        collection_name,
        json_location,
        mock_args(),
    )
    steps.generate_dataset_from_historical_audit.create_hive_table_on_published_for_collection(
            spark,
            collection_name,
            json_location,
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
    expected = [Row(first_name='abcd', last_name='xyz', date_str='2021-07-02'), Row(first_name='abcd', last_name='xyz', date_str='2021-07-02')]
    expected_json = json.dumps(expected)
    actual_json = json.dumps(managed_table_result)
    print(expected_json)
    print(actual_json)
    assert len(managed_table_result) == 1

    managed_table_raw_result = spark.sql(f"select * from uc_dw_auditlog.{managed_table_raw}").collect()
    print(managed_table_raw_result)
    expected = [Row(val='{"first_name":"abcd","last_name":"xyz"}', date_str='2021-07-07'), Row(val='{"first_name":"abcd","last_name":"xyz"}', date_str='2021-07-07')]
    expected_json = json.dumps(expected)
    actual_json = json.dumps(managed_table_raw_result)
    print(expected_json)
    print(actual_json)
    assert len(managed_table_result) == 1

def mock_get_audit_managed_file():
    return open("tests/auditlog_managed_table.sql")

def mock_get_audit_external_file():
    return open("tests/auditlog_external_table.sql")

def mock_args():
    args = argparse.Namespace()
    args.s3_prefix = f"{S3_PREFIX}/"
    args.snapshot_type = 'historical_business_audit'
    return args


def monkeypatch_with_mocks(monkeypatch):
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "decompress", mock_decompress)
    monkeypatch.setattr(
        steps.generate_dataset_from_historical_audit, "persist_json", mock_persist_json
    )
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "decrypt", mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "call_dks", mock_call_dks)
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "get_metadatafor_key", mock_get_metadatafor_key)
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "get_audit_managed_file", mock_get_audit_managed_file)
    monkeypatch.setattr(steps.generate_dataset_from_historical_audit, "get_audit_external_file", mock_get_audit_external_file)


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)

def mock_decrypt(plain_text_key, iv_key, data, args):
    return data

# Mocking because we don't have the compression codec libraries available in test phase
def mock_persist_json(json_location, values):
    values.saveAsTextFile(json_location)

def mock_call_dks(cek, kek, args):
    return kek

def mock_get_metadatafor_key(key, s3_client, s3_htme_bucket):
    return {
               "iv": "123",
               "ciphertext": "test_ciphertext",
               "datakeyencryptionkeyid": "123",
           }