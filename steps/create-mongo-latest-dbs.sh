(
# Import the logging functions
source /opt/emr/logging.sh

PROCESSED_BUCKET="${processed_bucket}"
PUBLISHED_BUCKET="${publish_bucket}"

function log_wrapper_message() {
    log_adg_message "$${1}" "create-mongo-latest-dbs.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
}

log_wrapper_message "Starts create-mongo-latest-dbs step"

#create mongo latest databasess
hive -e "CREATE DATABASE IF NOT EXISTS uc_mongo_latest LOCATION '$PROCESSED_BUCKET/uc_mongo_latest/data';" 
hive -e "CREATE DATABASE IF NOT EXISTS ucs_latest_unredacted LOCATION '$PUBLISHED_BUCKET/ucs_latest_unredacted/data';"
hive -e "CREATE DATABASE IF NOT EXISTS ucs_latest_redacted LOCATION  '$PUBLISHED_BUCKET/ucs_latest_redacted/data';"

log_wrapper_message "Completed the create-mongo-latest-dbs.sh step of the EMR Cluster"

) >> /var/log/adg/create-mongo-latest-dbs.log 2>&1
