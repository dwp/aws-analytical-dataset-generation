import boto3
import csv
import logging
import logger

level = "info"
logger_path = "/var/log/adg/hive_tables_creation_log.txt"
logger_format = "{ 'timestamp': '%(asctime)s', 'log_level': '%(levelname)s', 'message': '%(message)s' }"
the_logger = setup_logging(level, logger_path , logger_format)

client = boto3.client("glue")
DatabaseName = "analytical_dataset_generation_staging"
with open("current_hbase_tables") as f:
    hbase_tables = f.read()
with open("collections.csv") as csvfile:
    collections = csv.reader(csvfile, delimiter=",")
    for collection in collections:
        collection = collection[0]
        collection_hbase = collection.replace(":", "_") + "_hbase"
        if collection in hbase_tables:
            try:
                client.delete_table(DatabaseName=DatabaseName, Name=collection_hbase)
            except client.exceptions.EntityNotFoundException as e:
                the_logger.error(
                    "Exception cannot delete table: " + str(e)
                )  
            
            try:
                client.create_table(
                    DatabaseName=DatabaseName,
                    TableInput={
                        "Name": collection_hbase,
                        "Description": "Hive table to access hbase table " + collection,
                        "StorageDescriptor": {
                            "Columns": [
                                {"Name": "rowkey", "Type": "string"},
                                {"Name": "data", "Type": "string"},
                            ],
                            "Location": "s3://${bucket}/analytical-dataset/hive/external/"
                            + collection_hbase,
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
            except client.exceptions.EntityNotFoundException as e:
                the_logger.error(
                    "Exception cannot create table: " + collection_hbase
                )      
        else: 
            the_logger.error(collection, " is not in HBase")
            
