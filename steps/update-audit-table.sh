(
    function log_wrapper_message() {
        log_adg_message "$${1}" "update-audit-table.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
    }

    log_wrapper_message "Starts update-audit-table step"

    # Import the logging functions
    source /opt/emr/logging.sh

    # Import and execute resume step function
    source /opt/emr/resume_step.sh

    CORRELATION_ID=`cat /opt/emr/correlation_id.txt`
    RUN_ID=1
    DATA_PRODUCT="MONGO_LATEST"
    DATE=$(date '+%Y-%m-%d')
    STATUS="Completed"
    CURRENT_STEP="update-audit-table.sh"
    CLUSTER_ID=`cat /mnt/var/lib/info/job-flow.json | jq '.jobFlowId'`
    CLUSTER_ID=$${CLUSTER_ID//\"}
    S3_PREFIX=`cat /opt/emr/s3_prefix.txt`
    SNAPSHOT_TYPE=`cat /opt/emr/snapshot_type.txt`

    JSON_STRING=`cat /opt/emr/dynamo_schema.json`
    JSON_STRING=`jq '.Correlation_Id.S = "'$CORRELATION_ID'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.DataProduct.S = "'$DATA_PRODUCT'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Date.S = "'$DATE'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Run_Id.N = "'$RUN_ID'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Status.S = "'$STATUS'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.CurrentStep.S = "'$CURRENT_STEP'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Cluster_Id.S = "'$CLUSTER_ID'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.S3_Prefix_Snapshots.S = "'$S3_PREFIX'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Snapshot_Type.S = "'$SNAPSHOT_TYPE'"'<<<$JSON_STRING`

    dynamo_put_item() {
    JSON_STRING=$1
    aws dynamodb put-item  --table-name ${dynamodb_table_name} --item "$JSON_STRING"
    }

    dynamo_put_item "$JSON_STRING"

    log_wrapper_message "Completed update-audit-table step of the EMR Cluster"

) >> /var/log/adg/update-audit-table.log 2>&1

