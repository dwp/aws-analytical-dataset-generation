(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$${1}" "hive-setup.sh" "$${PID}"  "Running as: ,$USER"
}

log_wrapper_message "Copying create-hive-tables.py files from s3 to local"


aws s3 cp "${hive-scripts-path}"  .

sleep 3m

hbasetables=`echo 'list' | sudo -E hbase shell > current_hbase_tables`

log_wrapper_message "Listing the tables in Hbase and exporting it to a file current_hbase_tables $hbasetables "

sleep 10

log_wrapper_message "Running create-hive-tables.py "

sudo -E /usr/bin/python3.6 create-hive-tables.py >> /var/log/adg/create-hive-tables.log 2>&1

log_wrapper_message "Completed the hive-setup.sh step of the EMR Cluster"

setcleaner=`echo "cleaner_chore_switch false" | sudo -E hbase shell `

sleep 10m

refresh_meta=`echo "refresh_meta" | sudo -E hbase shell `

) >> /var/log/adg/nohup.log 2>&1


