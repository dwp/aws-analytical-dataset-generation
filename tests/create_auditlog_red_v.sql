CREATE EXTERNAL TABLE IF NOT EXISTS #{hivevar:uc_database}.auditlog_red_v(
  firstname_hash INT,
  lastname_hash INT)
PARTITIONED BY (date_str STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.orc.OrcSerde'
WITH SERDEPROPERTIES ("ignore.malformed.json" = "true")
STORED AS orc
LOCATION '#{hivevar:location_str}'
TBLPROPERTIES ('orc.compress'='ZLIB');
