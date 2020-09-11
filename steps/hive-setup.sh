#!/bin/bash
set -euo pipefail
(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$1" "hive-setup.sh" "$$" "Running as: $USER"
}

aws s3 cp "${hive-scripts-path}" /opt/emr/.
aws s3 cp "${generate_analytical_dataset}" /opt/emr/.
hive -e "CREATE DATABASE IF NOT EXISTS ${published_db}"

) >> /var/log/adg/nohup.log 2>&1


