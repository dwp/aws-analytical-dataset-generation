import ast
import zlib

import boto3
import pytest
from moto import mock_s3

import steps
from steps import generate_dataset_from_htme

MOTO_SERVER_URL = "http://127.0.0.1:5000"

DB_CORE_CONTRACT = 'db.core.contract'
DB_CORE_ACCOUNTS = 'db.core.accounts'
DB_CORE_CONTRACT_FILE_NAME = f'{DB_CORE_CONTRACT}.01002.4040.gz.enc'
DB_CORE_ACCOUNTS_FILE_NAME = f'{DB_CORE_ACCOUNTS}.01002.4040.gz.enc'
S3_PREFIX = 'mongo/ucdata'
S3_HTME_BUCKET = 'test'
S3_PUBLISH_BUCKET = 'target'
SECRETS = "{'collections_all': {'db.core.contract': 'crown'}}"
SECRETS_COLLECTIONS = {DB_CORE_CONTRACT: 'crown'}
KEYS_MAP = {"test_ciphertext": "test_key"}
RUN_TIME_STAMP = "10-10-2000_10-10-10"
PUBLISHED_DATABASE_NAME = "test_db"


def test_retrieve_secrets(monkeypatch):
    class MockSession:
        class Session:
            def client(self, service_name):
                class Client:
                    def get_secret_value(self, SecretId):
                        return {"SecretBinary": str.encode(SECRETS)}

                return Client()

    monkeypatch.setattr(boto3, 'session', MockSession)
    assert generate_dataset_from_htme.retrieve_secrets() == ast.literal_eval(SECRETS)


def test_get_collections():
    secret_dict = ast.literal_eval(SECRETS)
    assert generate_dataset_from_htme.get_collections(secret_dict) == SECRETS_COLLECTIONS


@mock_s3
def test_get_list_keys_for_prefix(aws_credentials):
    s3_client = boto3.client('s3')
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.put_object(Body="test", Bucket=S3_HTME_BUCKET, Key=f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}')

    assert (
            generate_dataset_from_htme.get_list_keys_for_prefix(s3_client, S3_HTME_BUCKET, S3_PREFIX) ==
            [f"{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}"]
    )


def test_group_keys_by_collection():
    keys = [f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}',
            f'{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}']
    assert (
            generate_dataset_from_htme.group_keys_by_collection(keys) ==
            [{f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}']},
             {f'{DB_CORE_ACCOUNTS}': [f'{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}']}]
    )


def test_get_collections_in_secrets():
    list_of_dicts = [{f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}']},
                     {f'{DB_CORE_ACCOUNTS}': [f'{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}']}]
    expected_list_of_dicts = [{f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}']}]
    assert generate_dataset_from_htme.get_collections_in_secrets(list_of_dicts,
                                                                 SECRETS_COLLECTIONS) == expected_list_of_dicts


@mock_s3
def test_consolidate_rdd_per_collection_with_one_collection(spark, monkeypatch, handle_server, aws_credentials):
    collection_name = "core_contract"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f'${{file_location}}/{RUN_TIME_STAMP}/{collection_name}/{collection_name}.json/part-00000'
    target_object_tag = {'Key': 'collection_tag', 'Value': 'crown'}
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    s3_client.put_object(Body=zlib.compress(test_data), Bucket=S3_HTME_BUCKET,
                         Key=f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}',
                         Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'add_metric', mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decompress', mock_decompress)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decrypt', mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'call_dks', mock_call_dks)
    generate_dataset_from_htme.main(spark, s3_client, S3_HTME_BUCKET, S3_PREFIX, SECRETS_COLLECTIONS, KEYS_MAP,
                                    RUN_TIME_STAMP, S3_PUBLISH_BUCKET, PUBLISHED_DATABASE_NAME)
    assert len(s3_client.list_buckets()['Buckets']) == 2
    assert (s3_client.get_object(Bucket=S3_PUBLISH_BUCKET,
                                 Key=target_object_key)['Body'].read().decode().strip() == test_data.decode())
    assert s3_client.get_object_tagging(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)['TagSet'][
               0] == target_object_tag
    assert collection_name in [x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)]


@mock_s3
def test_consolidate_rdd_per_collection_with_multiple_collections(spark, monkeypatch, handle_server, aws_credentials):
    core_contract_collection_name = "core_contract"
    core_accounts_collection_name = "core_accounts"
    test_data = '{"name":"abcd"}\n{"name":"xyz"}'
    secret_collections = SECRETS_COLLECTIONS
    secret_collections[DB_CORE_ACCOUNTS] = 'crown'
    s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_publish_bucket_for_multiple_collections = f"{S3_PUBLISH_BUCKET}-2"
    s3_client.create_bucket(Bucket=s3_publish_bucket_for_multiple_collections)
    s3_client.put_object(Body=zlib.compress(str.encode(test_data)), Bucket=S3_HTME_BUCKET,
                         Key=f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}',
                         Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
    s3_client.put_object(Body=zlib.compress(str.encode(test_data)), Bucket=S3_HTME_BUCKET,
                         Key=f'{S3_PREFIX}/{DB_CORE_ACCOUNTS_FILE_NAME}',
                         Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'add_metric', mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decompress', mock_decompress)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decrypt', mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'call_dks', mock_call_dks)
    generate_dataset_from_htme.main(spark, s3_client, S3_HTME_BUCKET, S3_PREFIX, secret_collections, KEYS_MAP,
                                    RUN_TIME_STAMP, s3_publish_bucket_for_multiple_collections, PUBLISHED_DATABASE_NAME)
    assert core_contract_collection_name in [x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)]
    assert core_accounts_collection_name in [x.name for x in spark.catalog.listTables(PUBLISHED_DATABASE_NAME)]


def test_create_hive_on_published(spark, handle_server, aws_credentials):
    json_location = "s3://test/t"
    collection_name = 'tabtest'
    all_processed_collections = [(collection_name, json_location)]
    steps.generate_dataset_from_htme.create_hive_tables_on_published(spark, all_processed_collections,
                                                                     PUBLISHED_DATABASE_NAME)
    assert generate_dataset_from_htme.get_collection(collection_name) in [x.name for x in
                                                                          spark.catalog.listTables(
                                                                              PUBLISHED_DATABASE_NAME)]


@mock_s3
def test_exception_when_decompression_fails(spark, monkeypatch, handle_server, aws_credentials):
    with pytest.raises(SystemExit) as ex:
        s3_client = boto3.client("s3", endpoint_url=MOTO_SERVER_URL)
        s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
        s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
        s3_client.put_object(Body=zlib.compress(b"test data"), Bucket=S3_HTME_BUCKET,
                             Key=f'{S3_PREFIX}/{DB_CORE_CONTRACT_FILE_NAME}',
                             Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
        monkeypatch.setattr(steps.generate_dataset_from_htme, 'add_metric', mock_add_metric)
        monkeypatch.setattr(steps.generate_dataset_from_htme, 'decrypt', mock_decrypt)
        monkeypatch.setattr(steps.generate_dataset_from_htme, 'call_dks', mock_call_dks)
        generate_dataset_from_htme.main(spark, s3_client, S3_HTME_BUCKET, S3_PREFIX, SECRETS_COLLECTIONS, KEYS_MAP,
                                        RUN_TIME_STAMP, S3_PUBLISH_BUCKET, PUBLISHED_DATABASE_NAME)


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)


def mock_add_metric(metrics_file, collection_name, value):
    return value


def mock_decrypt(plain_text_key, iv_key, data):
    return data


def mock_call_dks(cek, kek):
    return kek


def mock_create_hive_tables_on_published(spark, all_processed_collections, published_database_name):
    return published_database_name
