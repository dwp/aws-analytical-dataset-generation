CREATE EXTERNAL TABLE IF NOT EXISTS #{hivevar:uc_database}.auditlog_sec_v(
  1_abroad_for_more_than_one_month STRING)
PARTITIONED BY (date_str STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.orc.OrcSerde'
WITH SERDEPROPERTIES ("ignore.malformed.json" = "true")
STORED AS orc
LOCATION '#{hivevar:location_str}'
TBLPROPERTIES ('orc.compress'='ZLIB');
