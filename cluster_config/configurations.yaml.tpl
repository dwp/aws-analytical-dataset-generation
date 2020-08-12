---
Configurations:
- Classification: "yarn-site"
  Properties:
    "yarn.log-aggregation-enable": "true"
    "yarn.nodemanager.remote-app-log-dir": "s3://${s3_log_bucket}/${s3_log_prefix}/yarn"
    "yarn.nodemanager.vmem-check-enabled": "false"
- Classification: "spark"
  Properties:
    "maximizeResourceAllocation": "false"
- Classification: "spark-defaults"
  Properties:
    "spark.yarn.jars": "/usr/lib/spark/jars/*,/usr/lib/hbase/*,/usr/lib/hive/lib/hive-hbase-handler.jar,/usr/lib/hive/lib/metrics-core-2.2.0.jar,/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar,/opt/emr/metrics/dependencies/*"
    "spark.sql.catalogImplementation": "hive"
    "spark.yarn.dist.files": "/etc/spark/conf/hive-site.xml,/etc/hbase/conf/hbase-site.xml,/etc/pki/tls/private/private_key.key,/etc/pki/tls/certs/private_key.crt,/etc/pki/ca-trust/source/anchors/analytical_ca.pem"
    "spark.executor.extraClassPath": "/usr/lib/hadoop-lzo/lib/*:/usr/lib/hadoop/hadoop-aws.jar:/usr/share/aws/aws-java-sdk/*:/usr/share/aws/emr/emrfs/conf:/usr/share/aws/emr/emrfs/lib/*:/usr/share/aws/emr/emrfs/auxlib/*:/usr/share/aws/emr/goodies/lib/emr-spark-goodies.jar:/usr/share/aws/emr/security/conf:/usr/share/aws/emr/security/lib/*:/usr/share/aws/hmclient/lib/aws-glue-datacatalog-spark-client.jar:/usr/share/java/Hive-JSON-Serde/hive-openx-serde.jar:/usr/share/aws/sagemaker-spark-sdk/lib/sagemaker-spark-sdk.jar:/usr/share/aws/emr/s3select/lib/emr-s3-select-spark-connector.jar:/usr/lib/hive/lib/hive-hbase-handler.jar:/usr/lib/hbase/*:/usr/lib/hive/lib/metrics-core-2.2.0.jar:/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar:/opt/emr/metrics/dependencies/*"
    "spark.driver.extraClassPath": "/usr/lib/hadoop-lzo/lib/*:/usr/lib/hadoop/hadoop-aws.jar:/usr/share/aws/aws-java-sdk/*:/usr/share/aws/emr/emrfs/conf:/usr/share/aws/emr/emrfs/lib/*:/usr/share/aws/emr/emrfs/auxlib/*:/usr/share/aws/emr/goodies/lib/emr-spark-goodies.jar:/usr/share/aws/emr/security/conf:/usr/share/aws/emr/security/lib/*:/usr/share/aws/hmclient/lib/aws-glue-datacatalog-spark-client.jar:/usr/share/java/Hive-JSON-Serde/hive-openx-serde.jar:/usr/share/aws/sagemaker-spark-sdk/lib/sagemaker-spark-sdk.jar:/usr/share/aws/emr/s3select/lib/emr-s3-select-spark-connector.jar:/usr/lib/hive/lib/hive-hbase-handler.jar:/usr/lib/hbase/*:/usr/lib/hive/lib/metrics-core-2.2.0.jar:/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar:/opt/emr/metrics/dependencies/*"
    "spark.executor.extraJavaOptions": "-XX:+UseG1GC -XX:+UnlockDiagnosticVMOptions -XX:+G1SummarizeConcMark -XX:InitiatingHeapOccupancyPercent=35 -verbose:gc -XX:+PrintGCDetails -XX:+PrintGCDateStamps -XX:OnOutOfMemoryError='kill -9 %p' -Dhttp.proxyHost='${proxy_http_host}' -Dhttp.proxyPort='${proxy_http_port}' -Dhttp.nonProxyHosts='${proxy_no_proxy}' -Dhttps.proxyHost='${proxy_https_host}' -Dhttps.proxyPort='${proxy_https_port}'"
    "spark.driver.extraJavaOptions": "-XX:+UseG1GC -XX:+UnlockDiagnosticVMOptions -XX:+G1SummarizeConcMark -XX:InitiatingHeapOccupancyPercent=35 -verbose:gc -XX:+PrintGCDetails -XX:+PrintGCDateStamps -XX:OnOutOfMemoryError='kill -9 %p' -Dhttp.proxyHost='${proxy_http_host}' -Dhttp.proxyPort='${proxy_http_port}' -Dhttp.nonProxyHosts='${proxy_no_proxy}' -Dhttps.proxyHost='${proxy_https_host}' -Dhttps.proxyPort='${proxy_https_port}'"
    "spark.sql.warehouse.dir": "s3://${s3_published_bucket}/analytical-dataset/hive/external"
    "spark.executor.cores": "${spark_executor_cores}"
    "spark.executor.memory": "${spark_executor_memory}G"
    "spark.yarn.executor.memoryOverhead": "${spark_yarn_executor_memory_overhead}G"
    "spark.driver.memory": "${spark_driver_memory}G"
    "spark.driver.cores": "${spark_driver_cores}"
    "spark.executor.instances": "${spark_executor_instances}"
    "spark.default.parallelism": "${spark_default_parallelism}"

- Classification: "spark-hive-site"
  Properties:
    "hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
    "hbase.client.scanner.timeout.period": "1200000"
    "hbase.rpc.timeout": "1800000"
    "hbase.client.operation.timeout": "3600000"
    "hbase.scan.cache": "1000000"
    "hbase.scan.cacheblock": "false"
    "hbase.scan.batch": "2"

- Classification: "hive-site"
  Properties:
    "hive.metastore.schema.verification": "false"
    "hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
    "hive.metastore.warehouse.dir": "s3://${s3_published_bucket}/analytical-dataset/hive/external"
    "hbase.client.scanner.timeout.period": "1200000"
    "hbase.rpc.timeout": "1800000"
    "hbase.client.operation.timeout": "3600000"
- Classification: "emrfs-site"
  Properties:
    "fs.s3.consistent": "true"
    "fs.s3.consistent.metadata.read.capacity": "800"
    "fs.s3.consistent.metadata.write.capacity": "200"
    "fs.s3.maxConnections": "10000"
    "fs.s3.consistent.retryPolicyType": "fixed"
    "fs.s3.consistent.retryPeriodSeconds": "2"
    "fs.s3.consistent.retryCount": "10"
    "fs.s3.consistent.metadata.tableName": "${emrfs_metadata_tablename}"
- Classification: "spark-env"
  Configurations:
  - Classification: "export"
    Properties:
      "PYSPARK_PYTHON": "/usr/bin/python3"
      "S3_PUBLISH_BUCKET": "${s3_published_bucket}"
      "S3_HTME_BUCKET": "${s3_htme_bucket}"
