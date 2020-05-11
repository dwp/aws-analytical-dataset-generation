# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "${1}" "hive-setup.sh" "${3}" "Running as: ,$USER"
}

log_wrapper_message "Copying ${hive-scripts-path} and ${collections_list} files from s3 to local"

aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

sleep 3m

log_wrapper_message "Listing the tables in Hbase and exporting it to a file 'current_hbase_tables' "

echo 'list' | sudo -E hbase shell > current_hbase_tables

sleep 10

log_wrapper_message "Running create-hive-tables.py "

sudo -E /usr/bin/python3.6 create-hive-tables.py
