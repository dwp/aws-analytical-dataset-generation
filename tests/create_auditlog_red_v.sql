CREATE EXTERNAL TABLE IF NOT EXISTS #{hivevar:uc_database}.auditlog_red_v(
  1_abroad_for_more_than_one_month STRING)
PARTITIONED BY (date_str STRING)
STORED AS orc
LOCATION '#{hivevar:location_str}'
TBLPROPERTIES ('orc.compress'='ZLIB')