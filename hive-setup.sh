
aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

/usr/bin/python3.6 create-hive-tables.py