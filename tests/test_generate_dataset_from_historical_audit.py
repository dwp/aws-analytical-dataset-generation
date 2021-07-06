import argparse
import ast
import zlib
import requests
import time

import boto3
import pytest
from moto import mock_s3, mock_dynamodb2, mock_sns
from datetime import datetime

import steps
from steps import generate_dataset_from_historical_audit

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
        TAG_SET_FULL
        if mocked_args.snapshot_type == SNAPSHOT_TYPE_FULL
        else TAG_SET_INCREMENTAL
    )
    tbl_name = "businessAudit"
    collection_location = "data"
    collection_name = "businessAudit"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f"${{file_location}}/{collection_location}/{collection_name}/2021-07-02/part-00000"
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_resource = boto3.resource("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HISTORICAL_BUSINESS_AUDIT_BUCKET)
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
    monkeypatch_with_mocks(monkeypatch)
    generate_dataset_from_historical_audit.main(
        spark,
        s3_client,
        S3_HISTORICAL_BUSINESS_AUDIT_BUCKET,
        KEYS_MAP,
        S3_PUBLISH_BUCKET,
        PUBLISHED_DATABASE_NAME,
        mocked_args,
        s3_resource,
    )
    assert len(s3_client.list_buckets()["Buckets"]) == 2
    assert (
        s3_client.get_object(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)["Body"]
        .read()
        .decode()
        .strip()
        == test_data.decode()
    )


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