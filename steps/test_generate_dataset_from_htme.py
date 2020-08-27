import zlib

import boto3
import generate_dataset_from_htme
from moto import mock_s3


file_name = "db.core.contract.01002.4040.gz.enc"
s3_prefix = "mongo/ucdata"
s3_htme_bucket = "test"
s3_publish_bucket = "target"

def test_retrieve_secrets(monkeypatch, aws_credentials):
    class MockSession:
        class Session:
            def client(self, service_name):
                class Client:
                    def get_secret_value(self, SecretId):
                        return {"SecretBinary": str.encode("{'collections_all': {'db.core.contract': 'crown'}}")}

                return Client()

    monkeypatch.setattr(boto3, 'session', MockSession)
    assert generate_dataset_from_htme.retrieve_secrets() == {'collections_all': {'db.core.contract': 'crown'}}


def test_get_collections():
    secret_dict = {'collections_all': {'db.core.contract': 'crown'}}
    assert generate_dataset_from_htme.get_collections(secret_dict) == {'db.core.contract': 'crown'}


@mock_s3
def test_get_list_keys_for_prefix(monkeypatch, aws_credentials):
    s3_client = boto3.client('s3')
    s3_client.create_bucket(Bucket=s3_htme_bucket)
    s3_client.put_object(Body="test", Bucket=s3_htme_bucket, Key=f'{s3_prefix}/{file_name}')

    assert (
            generate_dataset_from_htme.get_list_keys_for_prefix(s3_client, s3_htme_bucket, s3_prefix) ==
            [f"{s3_prefix}/{file_name}"]
    )


def test_group_keys_by_collection():
    keys = [f'{s3_prefix}/{file_name}',
            f'{s3_prefix}/db.core.accounts.01002.4040.gz.enc']
    assert (
            generate_dataset_from_htme.group_keys_by_collection(keys) ==
            [{'db.core.contract': [f'{s3_prefix}/{file_name}']},
             {'db.core.accounts': [f'{s3_prefix}/db.core.accounts.01002.4040.gz.enc']}]
    )


def test_get_collections_in_secrets():
    list_of_dicts = [{'db.core.contract': [f'{s3_prefix}/{file_name}']},
                     {'db.core.accounts': [f'{s3_prefix}/db.core.accounts.01002.4040.gz.enc']}]
    secrets_collections = {'db.core.contract': 'crown'}
    expected_list_of_dicts = [{'db.core.contract': [f'{s3_prefix}/{file_name}']}]
    assert generate_dataset_from_htme.get_collections_in_secrets(list_of_dicts,
                                                                 secrets_collections) == expected_list_of_dicts


@mock_s3
def test_consolidate_rdd_per_collection(spark, monkeypatch, handle_server, aws_credentials):
    collection = {'db.core.contract': [f'{s3_prefix}/{file_name}']}
    secrets_collections = {'db.core.contract': 'crown'}
    collection_name = "core_contract"

    keys_map = {"test_ciphertext": "test_key"}
    run_time_stamp = "10-10-2000_10-10-10"
    published_database_name = "test_db"
    test_data = b'{"name":"abcd"}\n{"name":"xyz"}'
    target_object_key = f'${{file_location}}/{run_time_stamp}/{collection_name}/{collection_name}.json/part-00000'
    target_object_tag = {'Key': 'collection_tag', 'Value': 'crown'}
    s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")

    s3_client.create_bucket(Bucket=s3_htme_bucket)
    s3_client.create_bucket(Bucket=s3_publish_bucket)
    s3_client.put_object(Body=zlib.compress(test_data), Bucket=s3_htme_bucket, Key=f'{s3_prefix}/{file_name}',
                         Metadata={'iv': '123', 'ciphertext': 'test_ciphertext', 'datakeyencryptionkeyid': '123'})
    monkeypatch.setattr(generate_dataset_from_htme, 'add_metric', mock_add_metric)
    monkeypatch.setattr(generate_dataset_from_htme, 'decompress', mock_decompress)
    monkeypatch.setattr(generate_dataset_from_htme, 'decrypt', mock_decrypt)
    monkeypatch.setattr(generate_dataset_from_htme, 'call_dks', mock_call_dks)
    generate_dataset_from_htme.main(spark, s3_client, s3_htme_bucket, s3_prefix, secrets_collections, keys_map,
                                    run_time_stamp, s3_publish_bucket, published_database_name)
    generate_dataset_from_htme.consolidate_rdd_per_collection(collection, secrets_collections, s3_client,
                                                              s3_htme_bucket, spark, keys_map, run_time_stamp,
                                                              s3_publish_bucket, published_database_name)
    assert len(s3_client.list_buckets()['Buckets']) == 2
    assert len(s3_client.list_objects(Bucket=s3_publish_bucket)['Contents']) == 3
    assert (s3_client.get_object(Bucket=s3_publish_bucket,
                                 Key=target_object_key)['Body'].read().decode().strip() == test_data.decode())
    assert s3_client.get_object_tagging(Bucket=s3_publish_bucket, Key=target_object_key)['TagSet'][0] == target_object_tag


def mock_decompress(compressed_text):
    return zlib.decompress(compressed_text)


def mock_add_metric(metrics_file, collection_name, value):
    pass


def mock_decrypt(plain_text_key, iv_key, data):
    return data


def mock_call_dks(cek, kek):
    pass
