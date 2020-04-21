import boto3
import csv

collections = []
DatabaseName = "analytical_dataset_generation"
with open ('collections.csv', 'rb') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    for row in spamreader:
        collections.append(row)
        #print ', '.join(row)

client = boto3.client("glue")


for collection in collections:
    collection_hbase = collection + "_hbase"
    #make connection to happybase and check if table exists before creating it
    if client.get_table(DatabaseName=DatabaseName, Name= collection_hbase):
        client.delete_table(
            DatabaseName=DatabaseName, Name = collection_hbase
        )

    client.create_table(
        DatabaseName=DatabaseName,
        TableInput={
            "Name":collection_hbase,
            "Description": "Hive table to access hbase table " + collection,
            "StorageDescriptor": {
                "Columns": [
                    {"Name": "rowkey", "Type": "string"},
                    {"Name": "data", "Type": "string"},
                ],
                "Location": "s3://${bucket}/analytical-dataset/hive/external/" + collection_hbase,
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
