import json
from pyspark.sql import SparkSession
import base64
import binascii
import boto3
import os

import requests

from Crypto.Cipher import AES
from Crypto.Util import Counter
from pyspark.sql.types import *
from pyspark.sql import Row

from pysecret.aws import AWSSecret


def get_boto_session():
    session = None
    profile = os.environ.get("AWS_DEFAULT_PROFILE")
    role = os.environ.get("AWS_ASSUME_ROLE")
    if role:
        account = os.environ.get("AWS_ACCOUNT")
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=f"arn:aws:iam::{account}:role/{role}", RoleSessionName="GetSecret"
        )
        session = boto3.session.Session(
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
        )
    else:
        session = boto3.session.Session(profile_name=profile)
    return session._session


session = get_boto_session()
secret = AWSSecret(botocore_session=session)

S3_PUBLISH_BUCKET = secret.get_secret_value(
    secret_id="ADG-Payload", key="ADG_S3_PUBLISH_BUCKET"
)


def main():
    spark = (
        SparkSession.builder.master("yarn")
        .config("spark.sql.parquet.binaryAsString", "true")
        .appName("spike")
        .enableHiveSupport()
        .getOrCreate()
    )
    df = spark.sql("select * from hbase_hive")
    values = (
        df.select("data")
        .rdd.map(lambda x: getTuple(x.data))
        .map(lambda y: decrypt(y[0], y[1], y[2], y[3]))
    )
    print(type(values))
    # schema = StructType(List(
    # StructField("value", StringType(),True))
    # )
    # datadf = spark.createDataFrame(values,schema)
    row = Row("val")
    datadf = values.map(row).toDF()
    datadf.show()
    datadf.write.parquet(S3_PUBLISH_BUCKET("/xxx.parquet"))
    spark.sql(
        """CREATE EXTERNAL TABLE hive_spark_demo1(val STRING) STORED AS PARQUET LOCATION (S3_PUBLISH_BUCKET)"/source_table_parquet/xxxxx.parquet" """
    )
    spark.sql("select * from hive_spark_demo1").show()
    # getPrinted(values)


def decrypt(cek, kek, iv, ciphertext):
    url = "https://dks-development.mgt-dev.dataworks.dwp.gov.uk:8443/datakey/actions/decrypt"
    params = {"keyId": kek}
    result = requests.post(
        url,
        params=params,
        data=cek,
        cert=("/opt/emr/analytical.pem", "/opt/emr/analytical.key"),
        verify=False,
    )
    content = result.json()
    key = content["plaintextDataKey"]
    print("key--------->" + key)
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
