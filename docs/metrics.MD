# Metrics analysis

The Analytical Dataset Generation cluster consists of two main services:

- EMR Launcher
- The ADG EMR Cluster
    - The Glue DB

with the Glue DB as a subset of the Cluster.

The EMR Launcher is a short running job, and the ADG Cluster is a long running job.  Neither being good candidates for a regular metrics endpoint, and will likely require a push-gateway or an exporter.

Neither present a metrics endpoint natively.  The [Python Client](https://github.com/prometheus/client_python) is available, to instrument the EMR Launcher.  The EMR Cluster, however, will likely require its own exporter.  We could provisionally start by using the [CloudWatch Exporter](https://github.com/prometheus/cloudwatch_exporter).

### Metrics output

**_EMR Launcher_**

• Healthcheck (Counter)  
• Trigger (Counter)  
• Read config (Counter)  
• API Call (Counter)  
• API Response (Counter)  
• Exit (Counter)  

**_EMR Cluster_**

• Healthcheck (Counter)  
• Steps (Counter)  
• HBase reads (Gauge)  
• HBase Metadata writes (Counter)  
• Read config (Counter)  
• Read artefacts (Counter)  
• Hive writes (Gauge)  
• Parquet writes (Gauge)  
• Exit (Counter)  
