import json
from pyspark.sql import SparkSession
import base64
import binascii
import boto3
import ast
import requests
import re

from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql.types import *
from pyspark.sql import Row
from datetime import datetime
import logging
import pytz


def main():
    response_dict = retrieve_secrets()
    s3_publish_bucket = get_publish_bucket(response_dict)
    published_database_name = get_published_db_name()
    database_name = get_staging_db_name()
    spark = get_spark_session()
    tables = get_tables(database_name)
    for table_to_process in tables:
        adg_hive_table = database_name + "." + table_to_process
        adg_hive_select_query = "select * from %s" % adg_hive_table
        df = get_dataframe_from_staging(adg_hive_select_query, spark)
        keys_map = {}
        values = (
            df.select("data")
                .rdd.map(lambda x: getTuple(x.data))
                # TODO Is there a better way without tailing ?
                .map(lambda r: get_plaintext_key_calling_dks(r,keys_map))
                .map(lambda y: decrypt(y))
                .map(lambda p: validate(p))
                .map(lambda z: sanitize(z))
        )
        parquet_location = persist_parquet(s3_publish_bucket, table_to_process, values)
        create_hive_on_published(parquet_location, published_database_name, spark, table_to_process)

def get_publish_bucket(response_dict):
    try:
        S3_PUBLISH_BUCKET = response_dict["S3_PUBLISH_BUCKET"]
    except Exception:
        print(' key doesnt exist')
    return S3_PUBLISH_BUCKET


def create_hive_on_published(parquet_location, published_database_name, spark, table_to_process):
    src_hive_table = published_database_name + "." + table_to_process
    src_hive_drop_query = "DROP TABLE IF EXISTS %s" % src_hive_table
    src_hive_create_query = (
            """CREATE EXTERNAL TABLE IF NOT EXISTS %s(val STRING) STORED AS PARQUET LOCATION "%s" """
            % (src_hive_table, parquet_location)
    )
    spark.sql(src_hive_drop_query)
    spark.sql(src_hive_create_query)
    src_hive_select_query = "select * from %s" % src_hive_table
    spark.sql(src_hive_select_query).show()


def persist_parquet(S3_PUBLISH_BUCKET, table_to_process, values):
    print(f'and the values are {values.take(1)}')
    row = Row("val")
    datadf = values.map(row).toDF()
    datadf.show()
    adg_parquet_name = table_to_process + "." + "parquet"
    parquet_location = "s3://%s/${file_location}/%s" % (
        S3_PUBLISH_BUCKET,
        adg_parquet_name,
    )
    datadf.write.mode("overwrite").parquet(parquet_location)
    return parquet_location


def get_staging_db_name():
    database_name = "${staging_db}"
    return database_name


def get_published_db_name():
    published_database_name = "${published_db}"
    return published_database_name


def get_dataframe_from_staging(adg_hive_select_query, spark):
    df = spark.sql(adg_hive_select_query)
    return df


def get_spark_session():
    spark = (
        SparkSession.builder.master("yarn")
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator")
            .enableHiveSupport()
            .getOrCreate()
    )
    return spark


def retrieve_secrets():
    secret_name = "${secret_name}"
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    response_dict = ast.literal_eval(response["SecretString"])
    return response_dict

def validate(p):
    # TODO Can this decoding to an object happen at one place
    decrypted = p['decrypted']
    print(f'And the deccrypted is {decrypted}')
    db_object = json.loads(decrypted)
    id = retrieve_id(db_object)
    if isinstance(id, str):
        db_object =  replace_element_value_wit_key_value_pair(db_object, '_id', '$oid', id)
    wrap_dates(db_object)
    return p

def retrieve_id(db_object):
    id = db_object['_id']
    return id


def replace_element_value_wit_key_value_pair(db_object, key_to_replace, new_key, original_id):
    new_id = { new_key : original_id}
    db_object[key_to_replace] = new_id
    return db_object

def wrap_dates(db_object):
    last_modified_date_time_as_string = retrieve_last_modified_date_time(db_object)
    formatted_last_modified_string = format_date_to_valid_outgoing_format(last_modified_date_time_as_string)
    print(f"formatted_last_modified_string is {formatted_last_modified_string}")
    replace_element_value_wit_key_value_pair(db_object, '_lastModifiedDateTime', '$date', formatted_last_modified_string)

    created_date_time_as_string = retrieve_date_time_element('createdDateTime', db_object)
    if created_date_time_as_string:
        formatted_creates_datetime_string = format_date_to_valid_outgoing_format(created_date_time_as_string)
        print(f"formatted_creates_datetime_string is {formatted_creates_datetime_string}")
        replace_element_value_wit_key_value_pair(db_object, 'createdDateTime', '$date', formatted_creates_datetime_string )

    removed_date_time_as_string = retrieve_date_time_element('_removedDateTime', db_object)
    if removed_date_time_as_string:
        formatted_removed_date_time_as_string = format_date_to_valid_outgoing_format(removed_date_time_as_string)
        print(f"formatted_removed_date_time_as_string is {formatted_removed_date_time_as_string}")
        replace_element_value_wit_key_value_pair(db_object, '_removedDateTime', '$date', formatted_removed_date_time_as_string)

    archived_date_time_as_string = retrieve_date_time_element('_archivedDateTime', db_object)
    if archived_date_time_as_string:
        formatted_archived_date_time_as_string = format_date_to_valid_outgoing_format(archived_date_time_as_string)
        print(f"formatted_archived_date_time_as_string is {formatted_archived_date_time_as_string}")
        replace_element_value_wit_key_value_pair(db_object, '_archivedDateTime', '$date', formatted_archived_date_time_as_string)
    return db_object

def retrieve_last_modified_date_time(db_object):
    epoch = "1980-01-01T00:00:00.000Z"
    last_modified_date_time = retrieve_date_time_element('_lastModifiedDateTime', db_object)
    created_date_time = retrieve_date_time_element('createdDateTime', db_object)
    if last_modified_date_time:
        return last_modified_date_time
    if created_date_time:
        return created_date_time
    return epoch

def retrieve_date_time_element(key, db_object):
    print(f"retrieving {key}")
    date_element = db_object.get(key)
    print(f"date_element  is {date_element}")
    if date_element is not None:
        if isinstance(date_element, dict):
            date_sub_element =  date_element.get('$date')
            if date_sub_element is not None:
                return date_sub_element
        else:
            return date_element
    return ""

def format_date_to_valid_outgoing_format(current_date_time):
    parsed_date_time = get_valid_parsed_date_time(current_date_time)
    parsed_date_time.astimezone(pytz.utc)
    parsed_date_time = datetime.strftime(parsed_date_time, '%Y-%m-%dT%H:%M:%S.%f')
    (dt, micro) = parsed_date_time.split('.')
    dt = "%s.%03d%s" % (dt, int(micro) / 1000, 'Z')
    return dt

def get_valid_parsed_date_time(time_stamp_as_string):
    valid_timestamps =  ['%Y-%m-%dT%H:%M:%S.%fZ','%Y-%m-%dT%H:%M:%S.%f%z']
    for time_stamp_fmt in valid_timestamps:
        try:
            print(f"Trying format {time_stamp_fmt}")
            return datetime.strptime(time_stamp_as_string, time_stamp_fmt)
        except Exception:
            print(f'timestampAsString did not match valid format {time_stamp_fmt}')

    # TODO Think about the below exception later on
    raise Exception(f'Unparseable date found: {time_stamp_as_string} , did not match any supported date formats {valid_timestamps}')

def sanitize(z):
    decrypted = z['decrypted']
    db_name = z['db_name']
    collection_name = z['collection_name']
    print(f'And the deccrypted after validate is {decrypted} ')
    if ((db_name == "penalties-and-deductions" and collection_name == "sanction")
            or (db_name == "core" and collection_name == "healthAndDisabilityDeclaration")
            or (db_name == "accepted-data" and collection_name == "healthAndDisabilityCircumstances")):
        decrypted = re.sub(r'(?<!\\)\\[r|n]', '', decrypted)
    return decrypted.replace("$", "d_").replace("\u0000", "").replace("_archivedDateTime", "_removedDateTime").replace("_archived", "_removed")

def decrypt(y):
    key = y['plain_text_key']
    iv = y['iv']
    ciphertext = y['dbObject']
    iv_int = int(binascii.hexlify(base64.b64decode(iv)), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=ctr)
    print("about to decrypt")
    y['decrypted'] = aes.decrypt(base64.b64decode(ciphertext))
    return y

def get_plaintext_key_calling_dks(r,keys_map):
    cek = r['encryptedKey']
    kek = r['keyEncryptionkeyId']
    if keys_map.get(cek):
        key = keys_map[cek]
        print("Found the key in cache")
        r['plain_text_key'] = key
    else:
        print("Didn't find the key in cache so calling dks")
        key = call_dks(cek, kek)
        keys_map[cek] = key
        r['plain_text_key'] = key
    return r

def call_dks(cek, kek):
    url = "${url}"
    params = {"keyId": kek}
    result = requests.post(
        url,
        params=params,
        data=cek,
        cert=("private_key.crt", "private_key.key"),
        verify="analytical_ca.pem",
    )
    content = result.json()
    return content["plaintextDataKey"]

def getTuple(json_string):
    print(f'The json string is {json_string}')
    record = json.loads(json_string)
    encryption = record["message"]["encryption"]
    dbObject = record["message"]["dbObject"]
    encryptedKey = encryption["encryptedEncryptionKey"]
    keyEncryptionkeyId = encryption["keyEncryptionKeyId"]
    iv = encryption["initialisationVector"]
    # TODO  exception handling , what if the  below fields don't exist in the json
    db_name = record['message']['db']
    collection_name = record['message']['collection']
    return {
        "encryptedKey": encryptedKey,
        "keyEncryptionkeyId":keyEncryptionkeyId,
        "iv":iv,
        "dbObject":dbObject,
        "db_name":db_name,
        "collection_name":collection_name
    }

def getPrinted(values):
    for x in values:
        print(x)

def get_tables(db_name):
    table_list = []
    client = boto3.client("glue")
    tables_metadata_dict = client.get_tables(DatabaseName = db_name)
    db_tables = tables_metadata_dict["TableList"]
    for table_dict in db_tables:
        table_list.append(table_dict["Name"])
    return table_list


if __name__ == "__main__":
    main()
