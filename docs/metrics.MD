# Metrics analysis

The Analytical Dataset Generation cluster consists of two main services:

- EMR Launcher
- The ADG EMR Cluster
    - The Glue DB

with the Glue DB as a subset of the Cluster.

The EMR Launcher is a short running job, and the ADG Cluster is a long running job.  Neither being good candidates for a regular metrics endpoint, and will likely require a push-gateway or an exporter.

Neither present a metrics endpoint natively.  The [Python Client](https://github.com/prometheus/client_python) is available, to instrument the EMR Launcher.  The EMR Cluster, however, will likely require its own exporter.  We could provisionally start by using the [CloudWatch Exporter](https://github.com/prometheus/cloudwatch_exporter).  We will also investigate the [PrometheusSink](https://banzaicloud.com/blog/spark-prometheus-sink/) to get metrics from our Spark jobs.

Lastly we should consider basic instance-level metrics, such as CPU usage and memory usage etc.  Our AMI's now have the Prometheus NodeExporter as a base package, thus making instance-level metrics available by default.  Though there may be some consideration given to exposing the endpoint, in our infrastructure code.

### Metrics output

**_EMR Launcher_**

• Healthcheck (Counter)  
• Trigger (Counter)  
• Read config (Counter)  
• API Call (Counter)  
• API Response (Counter)  - (Success, Failure)
• Exit (Counter)  - (Success, Failure)

**_ADG Application_**

• Healthcheck (Counter) - (RUNNING || TERMINATED)  
• Steps (Counter) - (Total, Completed, Failed)  
• YARN applications total (Counter)  
• YARN applications succeeded (Counter)  
• YARN applications failed (Counter)  
• Jobs total (Counter)  
• Jobs succeeded (Counter)  
• Jobs failed (Counter)  
• Tasks total (Counter)  
• Tasks succeeded (Counter)  
• Tasks failed (Counter)  
• HBase reads (Gauge) - (Bytes || Scans)  
• Read config (Counter)  
• Read artefacts (Counter)  
• Parquet writes (Gauge)  
• HBase tables read (Counter)  
• Parquet tables written (Counter)  
• Glue tables written (Counter)  
• Garbage Collection stats Parquet tables written (Counter)  
• Exit (Counter) - (Success, Failure)  

**_GLUE_**

• writes (Gauge) 
• reads (Gauge)  
