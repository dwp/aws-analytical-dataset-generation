(
    # Import the logging functions
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

) >> /var/log/adg/create-mongo-latest-dbs.log 2>&1
