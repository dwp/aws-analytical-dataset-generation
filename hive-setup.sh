
aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

sleep 3m

echo 'list' | sudo -E hbase shell > current_hbase_tables

sleep 10

sudo -E /usr/bin/python3.6 create-hive-tables.py
