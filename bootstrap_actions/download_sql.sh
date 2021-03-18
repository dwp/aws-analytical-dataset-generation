(
    # Import the logging functions
    source /opt/emr/logging.sh

    function log_wrapper_message() {
        log_adg_message "$${1}" "download_sql.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
    }

    SCRIPT_DIR=/opt/emr/aws-mongo-latest

    echo "Download & install latest mongo latest scripts"
    log_wrapper_message "Downloading & install aws-mongo-latest scripts"

    VERSION="${version}"
    URL="s3://${s3_artefact_bucket_id}/aws-mongo-latest/aws-mongo-latest-$VERSION.zip"
    $(which aws) s3 cp $URL /opt/emr/

    echo "MONGO_LATEST_VERSION: $VERSION"
    log_wrapper_message "aws mongo latest version: $VERSION"

    echo "SCRIPT_DOWNLOAD_URL: $URL"
    log_wrapper_message "script_download_url: $URL"

    echo "Unzipping location: $SCRIPT_DIR"
    log_wrapper_message "script unzip location: $SCRIPT_DIR"

    echo "$version" > /opt/emr/version
    echo "${adg_log_level}" > /opt/emr/log_level
    echo "${environment_name}" > /opt/emr/environment

    echo "START_UNZIPPING ......................"
    log_wrapper_message "start unzipping ......................."

    unzip "/opt/emr/aws-mongo-latest-$VERSION.zip" -d "$SCRIPT_DIR"  >> /var/log/adg/download_unzip_sql.log 2>&1

    echo "FINISHED UNZIPPING ......................"
    log_wrapper_message "finished unzipping ......................."

)  >> /var/log/adg/download_sql.log 2>&1

