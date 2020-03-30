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
    secrets_manager = boto3.client('secretsmanager')
    response = secrets_manager.get_secret_value(
        SecretId="ADG-Payload"
    )
    S3_PUBLISH_BUCKET = response["ADG_S3_PUBLISH_BUCKET"]
    spark = (
        SparkSession.builder.master("yarn")
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator")
            .enableHiveSupport()
            .getOrCreate()
    )
    df = spark.sql("select * from core:contract")
    values = (
        df.select("data")
            .rdd.map(lambda x: getTuple(x.data))
            .map(lambda y: decrypt(y[0], y[1], y[2], y[3]))
    )
    row = Row("val")
    datadf = values.map(row).toDF()
    datadf.show()
    datadf.write.parquet(f"{S3_PUBLISH_BUCKET}/core_contract.parquet")
    spark.sql(
        f"CREATE EXTERNAL TABLE core_contract_src(val STRING) STORED AS PARQUET LOCATION {S3_PUBLISH_BUCKET})/core_contract.parquet"
    )
    spark.sql("select * from core_contract_src").show()

def decrypt(cek, kek, iv, ciphertext):
    url = "https://dks-development.mgt-dev.dataworks.dwp.gov.uk:8443/datakey/actions/decrypt"
    params = {"keyId": kek}
    result = requests.post(
        url,
        params=params,
        data=cek,
        cert=("/etc/pki/tls/certs/private_key.crt", "/etc/pki/tls/key/private_key.key"),
        verify=True,
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
