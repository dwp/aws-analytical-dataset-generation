# aws-analytical-dataset-generation

The Analytical Dataset Generation (ADG) cluster converts the latest versions of all records in specified HBase tables into Parquet files stored on S3. It then
generates Hive tables to provide downstream data processing & analytics tasks
with convenient SQL access to that data.

# Overview

![Overview](docs/overview.png)

1. At a defined time, a CloudWatch event will trigger the `EMR Launcher` Lambda function
1. The `EMR Launcher` reads EMR Cluster configuration files from the `Config` S3 bucket, then calls the `RunJobFlow` API of the EMR service which results in an
`Analytical Dataset Generator` (`ADG`) EMR cluster being launched
1. The `ADG Cluster` is configured as a read-replica of the `Ingest HBase` EMR
cluster; a PySpark step run on the cluster reads HBase Storefiles from the
`Input` S3 bucket and produces Parquet files in the `Output` S3 bucket.
1. The PySpark step then creates external Hive tables over those S3 objects,
storing the table definitions in a Glue database
1. Once processing is complete, the `ADG Cluster` terminates.


## Using AWS Insights for Analytical Dataset Generation analysis

As our logs go to cloudwatch, we can use AWS Insights to gather data and metrics about the ADG runs.

_Make sure you set the time range or you'll get odd results_

### Saving Insights for future use.

You can't. However, you can see previously used insights in the account (useful as you can't save them per se) by going to:
   > "CloudWatch | Logs | Insights (left menu bar) | Actions (button) | View query history for this account"

If you put a comment as the first line of a query it can do for a proxy title.

### Time taken for each Collection & Overall time taken for all Collections :
   ```
   # Time taken for each & all colletions   
   fields @timestamp , @message
   | parse @message "{ 'timestamp':* 'log_level':* 'message': 'time taken for*:*'" as timestamp ,log_level, collection, timetaken
   | display collection, timetaken
   | sort timetaken desc 
   ```

### How to add and run tests

1.	Pull the latest python3-pyspark-pytest image by running: `docker pull dwpdigital/python3-pyspark-pytest`
2.	Run: `docker run -it --rm --name adg-docker -v "$(pwd)":/install -w /install dwpdigital/python3-pyspark-pytest` 

### Known issues: 
1. make sure to delete locally generated directories  metastore_db, spark-temp, spark-warehouse directory if unit tests 
   fail when run locally 

