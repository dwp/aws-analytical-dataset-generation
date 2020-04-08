import boto3

client = boto3.client('glue')
client.create_table(
    DatabaseName='analytical_dataset_generation',
    TableInput={
        'Name': 'core_contract_hbase',
        'Description': 'Hive table to access hbase table core:contract',
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
            'Location': 's3://${bucket}/analytical-dataset/hive/external/core_contract_hbase',
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
            'EXTERNAL': 'True'
        }
    }
)
