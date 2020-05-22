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
