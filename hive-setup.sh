# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "${1}" "hive-setup.sh" "${PID}" "${@:2}" "Running as: ,$USER"
}

log_wrapper_message "Copying the s3 files"


aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

sleep 3m

log_wrapper_message "Listing the tables in Hbase to file "

echo 'list' | sudo -E hbase shell > current_hbase_tables

sleep 10

log_wrapper_message "Running create-hive-tables.py "

sudo -E /usr/bin/python3.6 create-hive-tables.py
