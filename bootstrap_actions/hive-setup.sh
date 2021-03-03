#!/bin/bash
set -euo pipefail
(
    # Import the logging functions
    source /opt/emr/logging.sh
    
    # Import and execute resume step function
    source /opt/emr/resume_step.sh

    function log_wrapper_message() {
        log_adg_message "$1" "hive-setup.sh" "$$" "Running as: $USER"
    }

    log_wrapper_message "Moving maria db jar to spark jars folder"
    sudo mkdir -p /usr/lib/spark/jars/
    sudo cp /usr/share/java/mariadb-connector-java.jar /usr/lib/spark/jars/

    log_wrapper_message "Setting up EMR steps folder"
    sudo mkdir -p /opt/emr/steps
    sudo chown hadoop:hadoop /opt/emr/steps

    log_wrapper_message "Creating init py file"
    touch /opt/emr/steps/__init__.py

    log_wrapper_message "Moving python steps files to steps folder"
    aws s3 cp "${python_logger}" /opt/emr/steps/.
    aws s3 cp "${python_resume_script}" /opt/emr/steps/.
    aws s3 cp "${generate_analytical_dataset}" /opt/emr/.

    log_wrapper_message "Creating external hive table"

    hive -e "CREATE DATABASE IF NOT EXISTS AUDIT; \
    DROP TABLE IF EXISTS AUDIT.data_pipeline_metadata_hive; \
    CREATE EXTERNAL TABLE IF NOT EXISTS AUDIT.data_pipeline_metadata_hive (Correlation_Id STRING, Run_Id BIGINT, \
    DataProduct STRING, DateProductRun STRING, Status STRING, CurrentStep STRING, Cluster_Id STRING, \
    S3_Prefix_Snapshots STRING, S3_Prefix_Analytical_DataSet STRING, Snapshot_Type STRING) \
    STORED BY 'org.apache.hadoop.hive.dynamodb.DynamoDBStorageHandler' \
    TBLPROPERTIES ('dynamodb.table.name'='${dynamodb_table_name}', \
    'dynamodb.column.mapping' = 'Correlation_Id:Correlation_Id,Run_Id:Run_Id,DataProduct:DataProduct,DateProductRun:Date,Status:Status,CurrentStep:CurrentStep,Cluster_Id:Cluster_Id,S3_Prefix_Snapshots:S3_Prefix_Snapshots,S3_Prefix_Analytical_DataSet:S3_Prefix_Analytical_DataSet,Snapshot_Type:Snapshot_Type','dynamodb.null.serialization' = 'true');"

    log_wrapper_message "Finished creating external hive table"
    
) >> /var/log/adg/hive_setup.log 2>&1


