import json
from pyspark.sql import SparkSession
import base64
import binascii
import boto3
import ast
import requests

from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql.types import *
from pyspark.sql import Row


def main():
    secret_name = "${secret_name}"
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    response_dict = ast.literal_eval(response["SecretString"])
    S3_PUBLISH_BUCKET = response_dict["S3_PUBLISH_BUCKET"]
    spark = (
        SparkSession.builder.master("yarn")
        .config("spark.sql.parquet.binaryAsString", "true")
        .appName("aws-analytical-dataset-generator")
        .enableHiveSupport()
        .getOrCreate()
    )

    database_name = "analytical_dataset_generation_staging"
    tables = getTables(database_name)
    for table_to_process in tables:   
        adg_hive_table = database_name + "." + table_to_process 
        adg_hive_select_query = "select * from %s" % adg_hive_table
        df = spark.sql(adg_hive_select_query)
        keys_map = {}
        values = (
            df.select("data")
            .rdd.map(lambda x: getTuple(x.data))
            .map(lambda y: decrypt(y[0], y[1], y[2], y[3], keys_map))
        )
        row = Row("val")
        datadf = values.map(row).toDF()
        datadf.show()
        adg_parquet_name = "core_contract.parquet"
        parquet_location = "s3://%s/analytical-dataset/%s" % (
            S3_PUBLISH_BUCKET,
            adg_parquet_name,
        )
        datadf.write.mode("overwrite").parquet(parquet_location)
        src_hive_table = "analytical_dataset_generation.core_contract"
        src_hive_drop_query = "DROP TABLE IF EXISTS %s" % src_hive_table
        src_hive_create_query = (
            """CREATE EXTERNAL TABLE IF NOT EXISTS %s(val STRING) STORED AS PARQUET LOCATION "%s" """
            % (src_hive_table, parquet_location)
        )
        spark.sql(src_hive_drop_query)
        spark.sql(src_hive_create_query)
        src_hive_select_query = "select * from %s" % src_hive_table
        spark.sql(src_hive_select_query).show()

def decrypt(cek, kek, iv, ciphertext, keys_map):
    if keys_map.get(cek):
        key = keys_map[cek]
        print("Found the key in cache")
    else:
        print("Didn't find the key in cache so calling dks")
        url = "https://dks-development.mgt-dev.dataworks.dwp.gov.uk:8443/datakey/actions/decrypt"
        params = {"keyId": kek}
        result = requests.post(
            url,
            params=params,
            data=cek,
            cert=("private_key.crt", "private_key.key"),
            verify="analytical_ca.pem",
        )
        content = result.json()
        key = content["plaintextDataKey"]
        keys_map[cek] = key
    iv_int = int(binascii.hexlify(base64.b64decode(iv)), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=ctr)
    print("about to decrypt")
    return aes.decrypt(base64.b64decode(ciphertext))


def getTuple(data):
    record = json.loads(data)
    encryption = record["message"]["encryption"]
    dbObject = record["message"]["dbObject"]
    encryptedKey = encryption["encryptedEncryptionKey"]
    keyEncryptionkeyId = encryption["keyEncryptionKeyId"]
    iv = encryption["initialisationVector"]
    return encryptedKey, keyEncryptionkeyId, iv, dbObject


def getPrinted(values):
    for x in values:
        print(x)

def getTables(db_name):
    table_list = []
    client = boto3.client("glue")
    tables_metadata_dict = client.get_tables(DatabaseName = db_name)
    tables_dict = tables_metadata_dict["TableList"]
    for table_dict in tables_dict:
       table_list.append(table_dict["Name"])
    return table_list



if __name__ == "__main__":
    main()
