import json
from pyspark.sql import SparkSession
import base64
import binascii
import boto3

import requests

from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql.types import *
from pyspark.sql import Row



def main():
    #secrets_manager = boto3.client('secretsmanager')
    #response = secrets_manager.get_secret_value(SecretId="ADG-Payload")
    #S3_PUBLISH_BUCKET = response["ADG_S3_PUBLISH_BUCKET"]
    S3_PUBLISH_BUCKET = "14f9b07948fa7b1e5440fd977a57c92d"
    spark = (
        SparkSession.builder.master("yarn")
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator")
            .enableHiveSupport()
            .getOrCreate()
    )
    adg_hive_table = "core_contract_adg"
    adg_hive_select_query = "select * from %s limit 10" % adg_hive_table
    df = spark.sql(adg_hive_select_query)
    values = (
        df.select("data")
            .rdd.map(lambda x: getTuple(x.data))
            .map(lambda y: decrypt(y[0], y[1], y[2], y[3]))
    )
    row = Row("val")
    datadf = values.map(row).toDF()
    datadf.show()
    adg_parquet_name = "core_contract.parquet"
    parquet_location = "s3://%s/adg/%s" % (S3_PUBLISH_BUCKET,adg_parquet_name)
    datadf.write.mode('overwrite').parquet(parquet_location)
    src_hive_table = "core_contract_src"
    src_hive_create_query = """CREATE EXTERNAL TABLE IF NOT EXISTS %s(val STRING) STORED AS PARQUET LOCATION "%s" """ % (src_hive_table, parquet_location)
    spark.sql(src_hive_create_query)
    src_hive_select_query = "select * from %s" % src_hive_table
    spark.sql(src_hive_select_query).show()

def decrypt(cek, kek, iv, ciphertext):
    url = "https://dks-development.mgt-dev.dataworks.dwp.gov.uk:8443/datakey/actions/decrypt"
    params = {"keyId": kek}
    result = requests.post(url,
                           params=params,
                           data=cek,
                           cert=("private_key.crt", "private_key.key"),
                           verify="analytical_ca.pem",
                           )
    content = result.json()
    key = content["plaintextDataKey"]
    iv_int = int(binascii.hexlify(base64.b64decode(iv)), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=ctr)
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

if __name__ == "__main__":
    main()
