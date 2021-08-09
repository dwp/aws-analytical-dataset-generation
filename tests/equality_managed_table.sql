CREATE TABLE IF NOT EXISTS ${hivevar:equality_database}.equality(
     type string,
     claimantid string,
     ethnicgroup string,
     ethnicitysubgroup string,
     sexualorientation string,
     religion string,
     maritalstatus string,
     load_date date)
STORED AS orc
TBLPROPERTIES ('orc.compress'='ZLIB');