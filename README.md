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
2.	Run: `docker run -it --rm --name adg-docker -v "$(pwd)":/install -w /install dwpdigital/python3-pyspark-pytest pytest .` 

### Known issues: 
1. make sure to delete locally generated directories  metastore_db, spark-temp, spark-warehouse directory if unit tests 
   fail when run locally
   
# Exporting application metrics

To export application metrics JMX exporter was chosen as it integrates with the existing metrics infrastructure and allows for metrics to be scraped by Prometheus.
 
## JMX set-up 

1.  Add jmx javagent to the [pom.xml](https://github.com/dwp/aws-analytical-dataset-generation/blob/DW-5340-documentation/bootstrap_actions/metrics_config/pom.xml) file that is used to download the jars
    
    ```
    <dependency>
        <groupId>io.prometheus.jmx</groupId>
        <artifactId>jmx_prometheus_javaagent</artifactId>
        <version>0.14.0</version>
    </dependency>
    ```
    this downloads jmx_javaagent jar from Maven. This has to happen as a bootstrap action as it needs to be present at application setup.

2. Edit [cluster launch configuration](https://github.com/dwp/aws-analytical-dataset-generation/blob/DW-5340-documentation/cluster_config/configurations.yaml.tpl) to start applications with Jmx exporter running as a javaagent.

    Eg. hadoop-env configuration
    ```
   - Classification: "hadoop-env"
     Configurations:
     - Classification: "export"
       Properties:
         "HADOOP_NAMENODE_OPTS": "\"-Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.local.only=false -Dcom.sun.management.jmxremote.port=7100 -javaagent:/opt/emr/metrics/dependencies/jmx_prometheus_javaagent-0.14.0.jar=7101:/opt/emr/metrics/prometheus_config.yml\""
         "HADOOP_DATANODE_OPTS": "\"-Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.local.only=false -Dcom.sun.management.jmxremote.port=7102 -javaagent:/opt/emr/metrics/dependencies/jmx_prometheus_javaagent-0.14.0.jar=7103:/opt/emr/metrics/prometheus_config.yml\""
   
   ```
   Javaagent needs to be configured to start on an unused port. If running multiple agents they need to run on different ports. In the hadoop-env example 7101, 7103.
   
3. Add an [ingress security group rule](https://github.com/dwp/dataworks-metrics-infrastructure/blob/master/peering_adg.tf#L89-L98) to accept Prometheus scraping on JMX exporter port.

4. Add an [egress security group rule](https://github.com/dwp/dataworks-metrics-infrastructure/blob/master/peering_adg.tf#L67-L76) to allow Prometheus to discover metrics on the JMX port.

5. Add a [scrape config](https://github.com/dwp/dataworks-metrics-infrastructure/blob/master/config/prometheus/prometheus-slave.yml#L91-L108) to Prometheus to discover metrics on the JMX exporter port.

6. Re-label the instances to differentiate between EMR nodes without mentioning the IP

    ```
    export AWS_DEFAULT_REGION=${aws_default_region}
    UUID=$(dbus-uuidgen | cut -c 1-8)
    TOKEN=$(curl -X PUT -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" "http://169.254.169.254/latest/api/token")
    export INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token:$TOKEN" -s http://169.254.169.254/latest/meta-data/instance-id)
    export INSTANCE_ROLE=$(jq .instanceRole /mnt/var/lib/info/extraInstanceData.json)
    export HOSTNAME=${name}-$${INSTANCE_ROLE//\"}-$UUID
    hostname $HOSTNAME
    aws ec2 create-tags --resources $INSTANCE_ID --tags Key=Name,Value=$HOSTNAME
    ```
    where `name` is the service name.
