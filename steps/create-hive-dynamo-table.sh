#!/bin/bash

set -euo pipefail
(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$1" "create-hive-dynamo-table.sh" "$$" "Running as: $USER"
}


log_wrapper_message "Starting hive script"

hive -e CREATE EXTERNAL TABLE data_pipeline_metadata_hive (Run_Id String, Correlation_Id String, DataProduct String, Status String, Date String)
STORED BY 'org.apache.hadoop.hive.dynamodb.DynamoDBStorageHandler'
TBLPROPERTIES ("dynamodb.table.name"={dynamodb_table_name},
"dynamodb.column.mapping" = "RunId:Run_Id, Correlation_Id: Correlation_Id, DataProduct: DataProduct, Status:Status, Date:Date",
"dynamodb.null.serialization" = "true");

) >> /var/log/adg/nohup.log 2>&1

log_wrapper_message "Finishing hive script"
