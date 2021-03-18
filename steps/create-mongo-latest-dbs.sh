(
    # Import the logging functions

    # shellcheck source=/opt/emr/logging.sh
    source /opt/emr/logging.sh

    # Import and execute resume step function
    source /opt/emr/resume_step.sh

    PROCESSED_BUCKET="${processed_bucket}"
    PUBLISHED_BUCKET="${publish_bucket}"

    function log_wrapper_message() {
        log_adg_message "$${1}" "create-mongo-latest-dbs.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
    }

    log_wrapper_message "Starts 'create-mongo-latest-dbs' step"

    #create mongo latest databasess
    hive -e "CREATE DATABASE IF NOT EXISTS uc_mongo_latest LOCATION '$PROCESSED_BUCKET/data/uc_mongo_latest';"
    hive -e "CREATE DATABASE IF NOT EXISTS ucs_latest_unredacted LOCATION '$PUBLISHED_BUCKET/data/ucs_latest_unredacted';"
    hive -e "CREATE DATABASE IF NOT EXISTS ucs_latest_redacted LOCATION  '$PUBLISHED_BUCKET/data/ucs_latest_redacted';"

    log_wrapper_message "Completed 'create-mongo-latest-dbs' step of the EMR Cluster"

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

) >> /var/log/adg/create-mongo-latest-dbs.log 2>&1
