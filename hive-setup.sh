
aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

sudo -E echo 'list' | sudo -E hbase shell > current_hbase_tables

/usr/bin/python3.6 -E  create-hive-tables.py