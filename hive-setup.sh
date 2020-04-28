
aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

sudo echo 'list' | hbase shell > current_hbase_tables

/usr/bin/python3.6 create-hive-tables.py