import ast
import zlib

import boto3
from moto import mock_s3

import steps
from steps import generate_dataset_from_htme

FILE_NAME = 'db.core.contract.01002.4040.gz.enc'
S3_PREFIX = 'mongo/ucdata'
S3_HTME_BUCKET = 'test'
S3_PUBLISH_BUCKET = 'target'
DB_CORE_CONTRACT = 'db.core.contract'
SECRETS = "{'collections_all': {'db.core.contract': 'crown'}}"
SECRETS_COLLECTIONS = {f'{DB_CORE_CONTRACT}': 'crown'}


def test_retrieve_secrets(monkeypatch, aws_credentials):
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
    s3_client.put_object(Body="test", Bucket=S3_HTME_BUCKET, Key=f'{S3_PREFIX}/{FILE_NAME}')

    assert (
            generate_dataset_from_htme.get_list_keys_for_prefix(s3_client, S3_HTME_BUCKET, S3_PREFIX) ==
            [f"{S3_PREFIX}/{FILE_NAME}"]
    )


def test_group_keys_by_collection():
    keys = [f'{S3_PREFIX}/{FILE_NAME}',
            f'{S3_PREFIX}/db.core.accounts.01002.4040.gz.enc']
    assert (
            generate_dataset_from_htme.group_keys_by_collection(keys) ==
            [{f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{FILE_NAME}']},
             {'db.core.accounts': [f'{S3_PREFIX}/db.core.accounts.01002.4040.gz.enc']}]
    )


def test_get_collections_in_secrets():
    list_of_dicts = [{f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{FILE_NAME}']},
                     {'db.core.accounts': [f'{S3_PREFIX}/db.core.accounts.01002.4040.gz.enc']}]
    expected_list_of_dicts = [{'db.core.contract': [f'{S3_PREFIX}/{FILE_NAME}']}]
    assert generate_dataset_from_htme.get_collections_in_secrets(list_of_dicts,
                                                                 SECRETS_COLLECTIONS) == expected_list_of_dicts


@mock_s3
def test_consolidate_rdd_per_collection(spark, monkeypatch, handle_server, aws_credentials):
    collection = {f'{DB_CORE_CONTRACT}': [f'{S3_PREFIX}/{FILE_NAME}']}
    collection_name = "core_contract"
    keys_map = {"test_ciphertext": "test_key"}
    run_time_stamp = "10-10-2000_10-10-10"
    published_database_name = "test_db"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f'${{file_location}}/{run_time_stamp}/{collection_name}/{collection_name}.json/part-00000'
    target_object_tag = {'Key': 'collection_tag', 'Value': 'crown'}
    s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")

    s3_client.create_bucket(Bucket=S3_HTME_BUCKET)
    s3_client.create_bucket(Bucket=S3_PUBLISH_BUCKET)
    s3_client.put_object(Body=zlib.compress(test_data), Bucket=S3_HTME_BUCKET, Key=f'{S3_PREFIX}/{FILE_NAME}',
                         Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'add_metric', mock_add_metric)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decompress', mock_decompress)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'decrypt', mock_decrypt)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'call_dks', mock_call_dks)
    monkeypatch.setattr(steps.generate_dataset_from_htme, 'create_hive_on_published', mock_create_hive_on_published)
    generate_dataset_from_htme.main(spark, s3_client, S3_HTME_BUCKET, S3_PREFIX, SECRETS_COLLECTIONS, keys_map,
                                    run_time_stamp, S3_PUBLISH_BUCKET, published_database_name)
    generate_dataset_from_htme.consolidate_rdd_per_collection(collection, SECRETS_COLLECTIONS, s3_client,
                                                              S3_HTME_BUCKET, spark, keys_map, run_time_stamp,
                                                              S3_PUBLISH_BUCKET, published_database_name)
    assert len(s3_client.list_buckets()['Buckets']) == 2
    assert len(s3_client.list_objects(Bucket=S3_PUBLISH_BUCKET)['Contents']) == 2
    assert (s3_client.get_object(Bucket=S3_PUBLISH_BUCKET,
                                 Key=target_object_key)['Body'].read().decode().strip() == test_data.decode())
    assert s3_client.get_object_tagging(Bucket=S3_PUBLISH_BUCKET, Key=target_object_key)['TagSet'][
               0] == target_object_tag


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)


def mock_add_metric(metrics_file, collection_name, value):
    return value


def mock_decrypt(plain_text_key, iv_key, data):
    return data


def mock_call_dks(cek, kek):
    return kek


# This need not be mocked on local dev machine but for some reason fails in Docker container, hence mocking this call.
def mock_create_hive_on_published(spark, json_location, collection_name, published_database_name):
    return collection_name
