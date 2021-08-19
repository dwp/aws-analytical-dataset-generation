CREATE TABLE IF NOT EXISTS #{hivevar:auditlog_database}.auditlog_managed (
     first_name STRING,
     last_name STRING,
     1_abroad_for_more_than_one_month STRING)
PARTITIONED BY (date_str STRING)
STORED AS orc
TBLPROPERTIES ('orc.compress'='ZLIB')
