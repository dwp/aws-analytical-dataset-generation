ALTER TABLE #{hivevar:uc_database}.auditlog_red_v ADD IF NOT EXISTS PARTITION(date_str='#{hivevar:date_hyphen}') LOCATION '#{hivevar:location_str}date_str=#{hivevar:date_hyphen}/';
INSERT OVERWRITE TABLE #{hivevar:uc_database}.auditlog_red_v PARTITION(date_str='#{hivevar:date_hyphen}')
SELECT #{hivevar:auditlog_red_v_columns} from #{hivevar:uc_dw_auditlog_database}.auditlog_managed where date_str = '#{hivevar:date_hyphen}';
