import boto3

client = boto3.client('glue')
client.delete_table(
    DatabaseName='analytical_dataset_generation',
    Name='core_contract_adg'
)
client.create_table(
    DatabaseName='analytical_dataset_generation',
    TableInput={
        'Name': 'core_contract_adg',
        'Description': 'db.core.contract',
        'StorageDescriptor': {
            'Columns': [
                {
                    'Name': 'rowkey',
                    'Type': 'string'
                },
                {
                    'Name': 'data',
                    'Type': 'string'
                }
            ],
            'Location': 's3://{REPLACE_THIS}/hive/external/core_contract_adg',
            'Compressed': False,
            'NumberOfBuckets': -1,
            'SerdeInfo': {
                'Name': 'string',
                'SerializationLibrary': 'org.apache.hadoop.hive.hbase.HBaseSerDe',
                'Parameters': {
                    'hbase.columns.mapping': ':key,cf:record',
                    'serialization.format': '1'
                }
            },
        },
        'TableType': 'EXTERNAL_TABLE',
        'Parameters': {
            'hbase.table.name': 'core:contract',
            'storage_handler':'org.apache.hadoop.hive.hbase.HBaseStorageHandler',
            'EXTERNAL': 'True',
            'totalSize': '0',
            'numRows': '0',
            'rawDataSize': '0',
            'COLUMN_STATS_ACCURATE': '{\"BASIC_STATS\":\"true\"}',
            'numFiles': '0'
        }
    }
)
