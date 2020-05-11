import boto3
import csv
import logging
import ast

client = boto3.client("glue")
# Create a Secrets Manager client
secret_name = "${secret_name}"
session = boto3.session.Session()
client_secret = session.client(service_name="secretsmanager")
response = client_secret.get_secret_value(SecretId=secret_name)
response_dict = ast.literal_eval(response["SecretString"])
collections_dict = response_dict["collections"]
collections_hbase = {key.replace('db.','',1):value for (key,value) in collections_dict.items()}
collections_hbase = {key.replace('.','_'):value for (key,value) in collections_hbase.items()}

DatabaseName = "analytical_dataset_generation_staging"
with open("current_hbase_tables") as f:
    hbase_tables = f.read()


for collection in collections_hbase:
    collection_staging = collection.replace(":", "_") + "_hbase"
    if collection in hbase_tables:
        try:
            client.delete_table(DatabaseName=DatabaseName, Name=collection_staging)
        except client.exceptions.EntityNotFoundException as e:
            logging.error(e)

        client.create_table(
            DatabaseName=DatabaseName,
            TableInput={
                "Name": collection_staging,
                "Description": "Hive table to access hbase table " + collection,
                "StorageDescriptor": {
                    "Columns": [
                        {"Name": "rowkey", "Type": "string"},
                        {"Name": "data", "Type": "string"},
                    ],
                    "Location": "s3://${bucket}/analytical-dataset/hive/external/"
                    + collection_staging,
                    "Compressed": False,
                    "NumberOfBuckets": -1,
                    "SerdeInfo": {
                        "Name": "string",
                        "SerializationLibrary": "org.apache.hadoop.hive.hbase.HBaseSerDe",
                        "Parameters": {
                            "hbase.columns.mapping": ":key,cf:record",
                            "serialization.format": "1",
                        },
                    },
                },
                "TableType": "EXTERNAL_TABLE",
                "Parameters": {
                    "hbase.table.name": collection,
                    "storage_handler": "org.apache.hadoop.hive.hbase.HBaseStorageHandler",
                    "EXTERNAL": "True",
                },
            },
        )
    else:
        logging.error(collection, " is not in HBase")


