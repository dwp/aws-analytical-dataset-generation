#!/bin/bash
set -euo pipefail
(
# Import the logging functions
source /opt/emr/logging.sh

function log_wrapper_message() {
    log_adg_message "$1" "hive-setup.sh" "$$" "Running as: $USER"
}

log_wrapper_message "Copying create-hive-tables.py files from s3 to local"

aws s3 cp "${hive-scripts-path}" /opt/emr/.

log_wrapper_message "Configuring HBase shell to use ingest-hbase cluster"
hbase_quorum=$(grep -A1 hbase.zookeeper.quorum /etc/hive/conf/hive-site.xml | grep value)
cat > hbase-site.xml << EOF
<configuration>
<property>
      <name>hbase.zookeeper.quorum</name>
      $hbase_quorum
</property>
</configuration>
EOF
sudo mv hbase-site.xml /etc/hbase/conf/

log_wrapper_message "Generating list of current HBase tables"
hbasetables=`echo 'list' | hbase shell > current_hbase_tables`
sudo mv current_hbase_tables /opt/emr/.

aws s3 cp "${python_logger}" /opt/emr/.
aws s3 cp "${generate_analytical_dataset}" /opt/emr/.

log_wrapper_message "Creating hive tables"

/usr/bin/python3.6 /opt/emr/create-hive-tables.py >> /var/log/adg/create-hive-tables.log 2>&1

log_wrapper_message "Completed the hive-setup.sh step of the EMR Cluster"

) >> /var/log/adg/nohup.log 2>&1


