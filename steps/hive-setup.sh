#!/bin/bash
set -euo pipefail
(
# Import the logging functions
source /opt/emr/logging.sh
sudo cp /usr/share/java/mariadb-connector-java.jar /usr/lib/spark/jars/
sudo mkdir -p /opt/emr/steps
sudo chown hadoop:hadoop /opt/emr/steps
touch /opt/emr/steps/__init__.py

function log_wrapper_message() {
    log_adg_message "$1" "hive-setup.sh" "$$" "Running as: $USER"
}
aws s3 cp "${python_logger}" /opt/emr/steps/.
aws s3 cp "${generate_analytical_dataset}" /opt/emr/.
) >> /var/log/adg/nohup.log 2>&1


