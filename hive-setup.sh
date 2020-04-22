
aws s3 cp "${hive-scripts-path}"  .
aws s3 cp "${collections_list}"  .

/usr/bin/python create-hive-tables.py