---
Configurations:
- Classification: "yarn-site"
  Properties:
    "yarn.log-aggregation.retain-seconds": "-1"
    "yarn.log-aggregation-enable": "true"
    "yarn.nodemanager.remote-app-log-dir": "s3://${s3_log_bucket}/logs/yarn"
- Classification: "spark"
  Properties:
    "maximizeResourceAllocation": "false"
- Classification: "spark-defaults"
  Properties:
    "spark.yarn.jars": "/usr/lib/spark/jars/*,/usr/lib/hbase/*,/usr/lib/hive/lib/hive-hbase-handler.jar,/usr/lib/hive/lib/metrics-core-2.2.0.jar,/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar"
    "spark.sql.catalogImplementation": "hive"
    "spark.yarn.dist.files": "/etc/spark/conf/hive-site.xml,/etc/hbase/conf/hbase-site.xml,/etc/pki/tls/private/private_key.key,/etc/pki/tls/certs/private_key.crt,/etc/pki/ca-trust/source/anchors/analytical_ca.pem"
    "spark.executor.extraClassPath": "/usr/lib/hadoop-lzo/lib/*:/usr/lib/hadoop/hadoop-aws.jar:/usr/share/aws/aws-java-sdk/*:/usr/share/aws/emr/emrfs/conf:/usr/share/aws/emr/emrfs/lib/*:/usr/share/aws/emr/emrfs/auxlib/*:/usr/share/aws/emr/goodies/lib/emr-spark-goodies.jar:/usr/share/aws/emr/security/conf:/usr/share/aws/emr/security/lib/*:/usr/share/aws/hmclient/lib/aws-glue-datacatalog-spark-client.jar:/usr/share/java/Hive-JSON-Serde/hive-openx-serde.jar:/usr/share/aws/sagemaker-spark-sdk/lib/sagemaker-spark-sdk.jar:/usr/share/aws/emr/s3select/lib/emr-s3-select-spark-connector.jar:/usr/lib/hive/lib/hive-hbase-handler.jar:/usr/lib/hbase/*:/usr/lib/hive/lib/metrics-core-2.2.0.jar:/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar"
    "spark.driver.extraClassPath": "/usr/lib/hadoop-lzo/lib/*:/usr/lib/hadoop/hadoop-aws.jar:/usr/share/aws/aws-java-sdk/*:/usr/share/aws/emr/emrfs/conf:/usr/share/aws/emr/emrfs/lib/*:/usr/share/aws/emr/emrfs/auxlib/*:/usr/share/aws/emr/goodies/lib/emr-spark-goodies.jar:/usr/share/aws/emr/security/conf:/usr/share/aws/emr/security/lib/*:/usr/share/aws/hmclient/lib/aws-glue-datacatalog-spark-client.jar:/usr/share/java/Hive-JSON-Serde/hive-openx-serde.jar:/usr/share/aws/sagemaker-spark-sdk/lib/sagemaker-spark-sdk.jar:/usr/share/aws/emr/s3select/lib/emr-s3-select-spark-connector.jar:/usr/lib/hive/lib/hive-hbase-handler.jar:/usr/lib/hbase/*:/usr/lib/hive/lib/metrics-core-2.2.0.jar:/usr/lib/hive/lib/htrace-core-3.1.0-incubating.jar"
    "spark.executor.extraJavaOptions": "-verbose:gc -XX:+PrintGCDetails -XX:+PrintGCDateStamps -XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=70 -XX:MaxHeapFreeRatio=70 -XX:+CMSClassUnloadingEnabled -XX:OnOutOfMemoryError='kill -9 %p' -Dhttp.proxyHost='${proxy_http_address}' -Dhttp.proxyPort='3128' -Dhttp.nonProxyHosts='${proxy_no_proxy}' -Dhttps.proxyHost='${proxy_http_address}' -Dhttps.proxyPort='3128'"
    "spark.driver.extraJavaOptions": "-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=70 -XX:MaxHeapFreeRatio=70 -XX:+CMSClassUnloadingEnabled -XX:OnOutOfMemoryError='kill -9 %p' -Dhttp.proxyHost='${proxy_http_address}' -Dhttp.proxyPort='3128' -Dhttp.nonProxyHosts='${proxy_no_proxy}' -Dhttps.proxyHost='${proxy_http_address}' -Dhttps.proxyPort='3128'"
    "spark.sql.warehouse.dir": "s3://${s3_published_bucket}/analytical-dataset/hive/external"
- Classification: "spark-hive-site"
  Properties:
    "hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
- Classification: "hive-site"
  Properties:
    "hive.metastore.schema.verification": "false"
    "hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
    "hive.metastore.warehouse.dir": "s3://${s3_published_bucket}/analytical-dataset/hive/external"
- Classification: "hbase-site"
  Properties:
    "hbase.server.keyvalue.maxsize": "750000000"
    "hbase.bulkload.retries.retryOnIOException": "true"
    "hbase.client.write.buffer": "8388608"
    "hbase.regionserver.handler.count": "4"
    "hbase.client.keyvalue.maxsize": "750000000"
    "hbase.bucketcache.bucket.sizes": "5120,9216,17408,33792,41984,50176,58368,66560,99328,132096,197632,263168,394240,525312,656384,787456,918528,1049600,1180672,1311744,1442816,1704960,1967104,2229248"
    "hbase.rootdir": "${hbase_root_path}"
- Classification: "hbase"
  Properties:
    "hbase.emr.storageMode": "s3"
    "hbase.emr.readreplica.enabled": "true"
- Classification: "emrfs-site"
  Properties:
    "fs.s3.consistent.retryPeriodSeconds": "3"
    "fs.s3.consistent": "false"
    "fs.s3.cse.materialsDescription.enabled": "true"
    "fs.s3.consistent.retryCount": "5"
    "fs.s3.consistent.metadata.tableName": "DataGen-metadata"
- Classification: "spark-env"
  Configurations:
  - Classification: "export"
    Properties:
      "PYSPARK_PYTHON": "/usr/bin/python3"
