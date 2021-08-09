DROP TABLE IF EXISTS #{hivevar:equality_database}.equality_#{hivevar:date_underscore};
CREATE EXTERNAL TABLE #{hivevar:equality_database}.equality_#{hivevar:date_underscore} (
     `message`STRUCT<
     `type`:STRING
     ,`claimantId`:STRING
     ,`ethnicGroup`:STRING
     ,`ethnicitySubgroup`:STRING
     ,`sexualOrientation`:STRING
     ,`religion`:STRING
     ,`maritalStatus`:STRING>)
ROW FORMAT SERDE '#{hivevar:serde}'
WITH SERDEPROPERTIES ("ignore.malformed.json" = "true")
STORED AS TEXTFILE
LOCATION '#{hivevar:data_location}';


INSERT INTO TABLE #{hivevar:equality_database}.equality_managed
SELECT
     `message`.`type` as `type`
     ,`message`.`claimantId` as `claimantId`
     ,`message`.`ethnicGroup` as `ethnicGroup`
     ,`message`.`ethnicitySubgroup` as `ethnicitySubgroup`
     ,`message`.`sexualOrientation` as `sexualOrientation`
     ,`message`.`religion`  as `religion`
     ,`message`.`maritalStatus` as `maritalStatus`
     ,CURRENT_DATE as load_date
FROM #{hivevar:equality_database}.equality_#{hivevar:date_underscore}
