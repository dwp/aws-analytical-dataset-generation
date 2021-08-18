CREATE EXTERNAL TABLE #{hivevar:auditlog_database}.auditlog_#{hivevar:date_underscore} (
     first_name STRING,
     last_name STRING,
     1_abroad_for_more_than_one_month STRING)
PARTITIONED BY (date_str STRING)
ROW FORMAT SERDE '#{hivevar:serde}'
WITH SERDEPROPERTIES ("ignore.malformed.json" = "true")
STORED AS TEXTFILE
LOCATION '#{hivevar:data_location}';

ALTER TABLE #{hivevar:auditlog_database}.auditlog_#{hivevar:date_underscore} ADD IF NOT EXISTS PARTITION(date_str='#{hivevar:date_hyphen}') LOCATION '#{hivevar:data_location}';
INSERT OVERWRITE TABLE #{hivevar:auditlog_database}.auditlog_managed SELECT * FROM #{hivevar:auditlog_database}.auditlog_#{hivevar:date_underscore};
DROP TABLE IF EXISTS #{hivevar:auditlog_database}.auditlog_#{hivevar:date_underscore}
