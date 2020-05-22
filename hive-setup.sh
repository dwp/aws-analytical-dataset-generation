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

setcleaner=`echo "cleaner_chore_switch false" | sudo -E hbase shell `

log_wrapper_message "Setting  hbase cleaner_chore_switch to false  $setcleaner "

# sleeping for 10 min, during the testing it was observed that the hbase read replica isn't ready for the spark job to run. This is
# because the region server and hbase meta table of read replica cluster need some time to replicate the master cluster meta and all the
# tables are made available.

sleep 10m

log_wrapper_message "Completed the hive-setup.sh step of the EMR Cluster"

) >> /var/log/adg/nohup.log 2>&1


