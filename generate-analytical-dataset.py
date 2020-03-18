import json
from pyspark.sql import SparkSession
import base64
import binascii

import requests

from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql.types import *
from pyspark.sql import Row

from pysecret import AWSSecret

aws_profile = "analytical_dataset_generator"
aws_region = "eu-west-2"
aws = AWSSecret(profile_name=aws_profile, region_name=aws_region)

S3_PUBLISH_BUCKET = aws.get_secret_value(
    secret_id="ADG-Payload", key="S3_PUBLISH_BUCKET")


def main():
    spark = SparkSession.builder.master("yarn").config(
        "spark.sql.parquet.binaryAsString", "true").appName("spike").enableHiveSupport().getOrCreate()
    df = spark.sql("select * from hbase_hive")
    values = df.select("data").rdd.map(lambda x:
                                       getTuple(x.data)).map(lambda y: decrypt(y[0], y[1], y[2], y[3]))
    print(type(values))
    # schema = StructType(List(
# StructField("value", StringType(),True))
  # )
    #datadf = spark.createDataFrame(values,schema)
    row = Row("val")
    datadf = values.map(row).toDF()
    datadf.show()
    datadf.write.parquet("S3_PUBLISH_BUCKET/xxx.parquet")
    spark.sql("""CREATE EXTERNAL TABLE hive_spark_demo1(val STRING) STORED AS PARQUET LOCATION "S3_PUBLISH_BUCKET/source_table_parquet/xxxxx.parquet" """)
    spark.sql("select * from hive_spark_demo1").show()
    # getPrinted(values)


def decrypt(cek, kek, iv, ciphertext):
    url = 'https://dks-development.mgt-dev.dataworks.dwp.gov.uk:8443/datakey/actions/decrypt'
    params = {'keyId': kek}
    result = requests.post(url, params=params, data=cek, cert=(
        '/opt/emr/analytical.pem', '/opt/emr/analytical.key'), verify=False)
    content = result.json()
    key = content['plaintextDataKey']
    print("key--------->"+key)
    iv_int = int(binascii.hexlify(base64.b64decode(iv)), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=ctr)
    return aes.decrypt(base64.b64decode(ciphertext))


def getTuple(data):
    record = json.loads(data)
    encryption = record['message']['encryption']
    dbObject = record['message']['dbObject']
    encryptedKey = encryption['encryptedEncryptionKey']
    keyEncryptionkeyId = encryption['keyEncryptionKeyId']
    iv = encryption['initialisationVector']
    return encryptedKey, keyEncryptionkeyId, iv, dbObject


def getPrinted(values):
    for x in values:
        print(x)


if __name__ == "__main__":
    main()
