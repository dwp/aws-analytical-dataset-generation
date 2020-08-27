import ast
import base64
import binascii
import concurrent.futures
import datetime
import json
import logging
import os
import re
import time

import boto3
import requests
import pytz
from Crypto.Cipher import AES
from Crypto.Util import Counter
from steps.logger import setup_logging
from pyspark.sql import Row, SparkSession
from pyspark.sql.types import *
from pyspark.sql import functions as F

keys_map = {} # for caching dks key

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


class CollectionData:
    def __init__(self, collection_name, staging_hive_table, tag_value):
        self.collection_name = collection_name
        self.staging_hive_table = staging_hive_table
        self.tag_value = tag_value


def main():
    database_name = get_staging_db_name()
    secrets_response = retrieve_secrets()
    collections = get_collections(secrets_response)
    tables = get_tables(database_name)
    collection_objects = []
    for table_to_process in tables:
        collection_name = table_to_process.replace("_hbase", "")
        if collection_name in collections:
            staging_hive_table = database_name + "." + table_to_process
            tag_value = collections[collection_name]
            collection_name_object = CollectionData(
                collection_name, staging_hive_table, tag_value
            )
            collection_objects.append(collection_name_object)
        else:
            logging.error(
                table_to_process +
                "from staging_db is not present in the collections list ",
            )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(spark_process, collection_objects)


def spark_process(collection):
    start_timer = time.perf_counter()
    adg_hive_select_query = "select * from %s" % collection.staging_hive_table
    the_logger.info("Processing table : " + collection.staging_hive_table)
    df = get_dataframe_from_staging(adg_hive_select_query)
    raw_df  = df.select(df.data,F.get_json_object(df.data, "$.message.encryption.encryptedEncryptionKey").alias("encryptedKey"),
    F.get_json_object(df.data, "$.message.encryption.keyEncryptionKeyId").alias("keyEncryptionKeyId"),
    F.get_json_object(df.data, "$.message.encryption.initialisationVector").alias("iv"),
    # The below piece of code is  commented and worked around as its truncating the db object
    #F.get_json_object(df.data, "$.message.dbObject").alias("dbObject"),
    F.get_json_object(df.data, "$.message.db").alias("db_name"),
    F.get_json_object(df.data, "$.message.collection").alias("collection_name"),
    F.get_json_object(df.data, "$.message._id").alias("id"))
    key_df =  raw_df.withColumn("key",get_plain_key(raw_df["encryptedKey"], raw_df["keyEncryptionKeyId"]))
    decrypted_df = key_df.withColumn("decrypted_db_object", decryption(key_df["key"], key_df["iv"], key_df["data"]))
    validated_df = decrypted_df.withColumn("validated_db_object", validation(decrypted_df["decrypted_db_object"]))
    sanitised_df = validated_df.withColumn("sanitised_db_object", sanitise(validated_df["validated_db_object"], validated_df["db_name"], validated_df["collection_name"]))
    clean_df = sanitised_df.withColumnRenamed("sanitised_db_object", "val")
    values = clean_df.select("val")
    the_logger.info("Persisting Json : " + collection.collection_name)
    json_location = persist_json(collection.collection_name, values)
    prefix = (
        "${file_location}/"
        + collection.collection_name
        + "/"
        + collection.collection_name
        + ".json"
    )
    tag_objects(prefix, tag_value=collection.tag_value)
    create_hive_on_published(json_location, collection.collection_name)
    end_timer = time.perf_counter()
    time_taken = round(end_timer - start_timer)
    time_taken = str(time_taken)
    the_logger.info(f"time taken in seconds for {collection.collection_name}: {time_taken} ")


def retrieve_secrets():
    secret_name = "${secret_name}"
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    response_binary = response["SecretBinary"]
    response_decoded = response_binary.decode("utf-8")
    response_dict = ast.literal_eval(response_decoded)
    return response_dict

def get_collections(secrets_response):
    try:
        collections = secrets_response["collections_all"]
        collections = {
            key.replace("db.", "", 1): value for (key, value) in collections.items()
        }
        collections = {
            key.replace(".", "_"): value for (key, value) in collections.items()
        }
        collections = {
            key.replace("-", "_"): value for (key, value) in collections.items()
        }
        collections = {k.lower(): v.lower() for k, v in collections.items()}

    except Exception as e:
        logging.error("Problem with collections list", e)
    return collections


def create_hive_on_published(json_location, collection_name):
    src_hive_table = published_database_name + "." + collection_name
    src_hive_drop_query = "DROP TABLE IF EXISTS %s" % src_hive_table
    src_hive_create_query = (
        """CREATE EXTERNAL TABLE IF NOT EXISTS %s(val STRING) STORED AS TEXTFILE LOCATION "%s" """
        % (src_hive_table, json_location)
    )
    spark.sql(src_hive_drop_query)
    spark.sql(src_hive_create_query)
    return None


def persist_json(collection_name, values):
    adg_json_name = collection_name + "." + "json"
    json_location = "s3://%s/${file_location}/%s/%s" % (
        s3_publish_bucket,
        collection_name,
        adg_json_name,
    )
    values.write.mode("overwrite").text(json_location)
    return json_location


def tag_objects(prefix, tag_value):
    session = boto3.session.Session()
    client_s3 = session.client(service_name="s3")
    default_value = "default"

    if tag_value is None or tag_value == "":
        tag_value = default_value
    for key in client_s3.list_objects(Bucket=s3_publish_bucket, Prefix=prefix)[
        "Contents"
    ]:
        client_s3.put_object_tagging(
            Bucket=s3_publish_bucket,
            Key=key["Key"],
            Tagging={"TagSet": [{"Key": "collection_tag", "Value": tag_value}]},
        )


def get_staging_db_name():
    database_name = "${staging_db}"
    return database_name


def get_published_db_name():
    published_database_name = "${published_db}"
    return published_database_name


def get_dataframe_from_staging(adg_hive_select_query):
    df = spark.sql(adg_hive_select_query)
    return df


def get_spark_session():
    spark = (
        SparkSession.builder.master("yarn")
        .config("spark.sql.parquet.binaryAsString", "true")
        .config("spark.metrics.conf", "/opt/emr/metrics/metrics.properties")
        .config("spark.metrics.namespace", "adg")
        .appName("aws-analytical-dataset-generator")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.conf.set("spark.scheduler.mode", "FAIR")
    return spark


def validate(decrypted):
    db_object = json.loads(decrypted)
    id = retrieve_id(db_object)
    if isinstance(id, str):
        db_object =  replace_element_value_wit_key_value_pair(db_object, '_id', '$oid', id)
    validated_db_obj = wrap_dates(db_object)
    return json.dumps(validated_db_obj)


def retrieve_id(db_object):
    id = db_object["_id"]
    return id


def replace_element_value_wit_key_value_pair(
    db_object, key_to_replace, new_key, original_id
):
    new_id = {new_key: original_id}
    db_object[key_to_replace] = new_id
    return db_object


def wrap_dates(db_object):
    last_modified_date_time_as_string = retrieve_last_modified_date_time(db_object)
    formatted_last_modified_string = format_date_to_valid_outgoing_format(
        last_modified_date_time_as_string
    )
    replace_element_value_wit_key_value_pair(
        db_object, "_lastModifiedDateTime", "$date", formatted_last_modified_string
    )

    created_date_time_as_string = retrieve_date_time_element(
        "createdDateTime", db_object
    )
    if created_date_time_as_string:
        formatted_creates_datetime_string = format_date_to_valid_outgoing_format(
            created_date_time_as_string
        )
        replace_element_value_wit_key_value_pair(
            db_object, "createdDateTime", "$date", formatted_creates_datetime_string
        )

    removed_date_time_as_string = retrieve_date_time_element(
        "_removedDateTime", db_object
    )
    if removed_date_time_as_string:
        formatted_removed_date_time_as_string = format_date_to_valid_outgoing_format(
            removed_date_time_as_string
        )
        replace_element_value_wit_key_value_pair(
            db_object,
            "_removedDateTime",
            "$date",
            formatted_removed_date_time_as_string,
        )

    archived_date_time_as_string = retrieve_date_time_element(
        "_archivedDateTime", db_object
    )
    if archived_date_time_as_string:
        formatted_archived_date_time_as_string = format_date_to_valid_outgoing_format(
            archived_date_time_as_string
        )
        replace_element_value_wit_key_value_pair(
            db_object,
            "_archivedDateTime",
            "$date",
            formatted_archived_date_time_as_string,
        )
    return db_object


def retrieve_last_modified_date_time(db_object):
    epoch = "1980-01-01T00:00:00.000Z"
    last_modified_date_time = retrieve_date_time_element(
        "_lastModifiedDateTime", db_object
    )
    created_date_time = retrieve_date_time_element("createdDateTime", db_object)
    if last_modified_date_time:
        return last_modified_date_time
    if created_date_time:
        return created_date_time
    return epoch


def retrieve_date_time_element(key, db_object):
    date_element = db_object.get(key)
    if date_element is not None:
        if isinstance(date_element, dict):
            date_sub_element = date_element.get("$date")
            if date_sub_element is not None:
                return date_sub_element
        else:
            return date_element
    return ""


def format_date_to_valid_outgoing_format(current_date_time):
    parsed_date_time = get_valid_parsed_date_time(current_date_time)
    parsed_date_time.astimezone(pytz.utc)
    parsed_date_time = datetime.datetime.strftime(parsed_date_time, "%Y-%m-%dT%H:%M:%S.%f")
    (dt, micro) = parsed_date_time.split(".")
    dt = "%s.%03d%s" % (dt, int(micro) / 1000, "Z")
    return dt


def get_valid_parsed_date_time(time_stamp_as_string):
    valid_timestamps = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f%z"]
    for time_stamp_fmt in valid_timestamps:
        try:
            return datetime.datetime.strptime(time_stamp_as_string, time_stamp_fmt)
        except:
            pass
            #print(f"timestampAsString did not match valid format {time_stamp_fmt}")

    # TODO Think about the below exception later on
    raise Exception(
        f"Unparseable date found: {time_stamp_as_string} , did not match any supported date formats {valid_timestamps}"
    )


def sanitize(decrypted, db_name, collection_name):
    if ((db_name == "penalties-and-deductions" and collection_name == "sanction")
            or (db_name == "core" and collection_name == "healthAndDisabilityDeclaration")
            or (db_name == "accepted-data" and collection_name == "healthAndDisabilityCircumstances")):
        decrypted = re.sub(r'(?<!\\)\\[r|n]', '', decrypted)
    if type(decrypted) is bytes:
        decrypted = decrypted.decode("utf-8")
    return decrypted.replace("$", "d_").replace("\u0000", "").replace("_archivedDateTime", "_removedDateTime").replace("_archived", "_removed")

def decrypt(plain_text_key, iv_key, data):
    data_obj = json.loads(data)
    dbObject = data_obj["message"]["dbObject"]
    iv_int = int(binascii.hexlify(base64.b64decode(iv_key)), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(plain_text_key), AES.MODE_CTR, counter=ctr)
    decrypted = aes.decrypt(base64.b64decode(dbObject))
    #TODO Check if this conversion is needed later on
    if type(decrypted) is bytes:
        decrypted = decrypted.decode("utf-8")
    return decrypted


def get_plaintext_key_calling_dks(encryptedKey, keyEncryptionkeyId):
    if keys_map.get(encryptedKey):
        key = keys_map[encryptedKey]
    else:
        key = call_dks(encryptedKey, keyEncryptionkeyId)
        keys_map[encryptedKey] = key
    return key


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



def get_tables(db_name):
    table_list = []
    client = boto3.client("glue")
    tables_metadata_dict = client.get_tables(DatabaseName=db_name)
    db_tables = tables_metadata_dict["TableList"]
    for table_dict in db_tables:
        table_list.append(table_dict["Name"].lower())
    return table_list


if __name__ == "__main__":
    spark = get_spark_session()
    get_plain_key = F.udf(get_plaintext_key_calling_dks, StringType())
    decryption = F.udf(decrypt, StringType())
    validation = F.udf(validate, StringType())
    sanitise = F.udf(sanitize, StringType())
    s3_publish_bucket = os.getenv("S3_PUBLISH_BUCKET")
    published_database_name = get_published_db_name()
    database_name = get_staging_db_name()
    start_time = time.perf_counter()
    main()
    end_time = time.perf_counter()
    total_time = round(end_time - start_time)
    total_time = str(total_time)
    the_logger.info(f"time taken in seconds for all collections: {total_time} ")
