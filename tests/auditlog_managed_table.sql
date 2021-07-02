CREATE TABLE IF NOT EXISTS #{hivevar:auditlog_database}.auditlog_managed (
    first_name STRING,
    last_name STRING)
PARTITIONED BY (date_str STRING)
STORED AS orc
TBLPROPERTIES ('orc.compress'='ZLIB');