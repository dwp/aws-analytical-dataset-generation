#!/bin/bash

set -euo pipefail
(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$1" "create-hive-dynamo-table.sh" "$$" "Running as: $USER"
}


log_wrapper_message "Creating external hive table"

hive -e "CREATE EXTERNAL TABLE IF NOT EXISTS data_pipeline_metadata_hive \
(Correlation_Id STRING, Run_Id BIGINT, DataProduct STRING, Dates STRING, Status STRING) \
STORED BY 'org.apache.hadoop.hive.dynamodb.DynamoDBStorageHandler' \
TBLPROPERTIES ('dynamodb.table.name'={dynamodb_table_name}, \
'dynamodb.column.mapping' = 'Correlation_Id:Correlation_Id,Run_Id:Run_Id,DataProduct:DataProduct,Dates:Date,Status:Status', \
'dynamodb.null.serialization' = 'true');
CREATE EXTERNAL TABLE s3_export(a_col string, b_col bigint, c_col array<string>)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
LOCATION 's3://bucketname/path/subpath/';

INSERT OVERWRITE TABLE s3_export SELECT *
FROM hiveTableName; "
) >> /var/log/adg/nohup.log 2>&1

log_wrapper_message "Finished creating external hive table"
