---
Applications:
- Name: "Spark"
- Name: "Hive"
- Name: "HBase"
- Name: "Ganglia"
CustomAmiId: "${ami_id}"
EbsRootVolumeSize: 100
LogUri: "s3://${s3_log_bucket}/logs"
Name: "analytical-dataset-generator"
ReleaseLabel: "emr-5.24.1"
ScaleDownBehavior: "TERMINATE_AT_TASK_COMPLETION"
SecurityConfiguration: "${security_configuration}"
ServiceRole: "${service_role}"
JobFlowRole: "${instance_profile}"
VisibleToAllUsers: True
Tags:
- Key: "Persistence"
  Value: "Ignore"
- Key: "Owner"
  Value: "dataworks platform"
- Key: "AutoShutdown"
  Value: "False"
- Key: "CreatedBy"
  Value: "emr-launcher"
- Key: "SSMEnabled"
  Value: "True"
- Key: "Environment"
  Value: "development"
- Key: "Application"
  Value: "aws-analytical-dataset-generator"
- Key: "Name"
  Value: "aws-analytical-dataset-generator"
