---
Applications:
- Name: "Spark"
- Name: "Ganglia"
- Name: "Hive"
CustomAmiId: "${ami_id}"
EbsRootVolumeSize: 100
LogUri: "s3://${s3_log_bucket}/${s3_log_prefix}"
Name: "analytical-dataset-generator"
ReleaseLabel: "emr-${emr_release}"
SecurityConfiguration: "${security_configuration}"
ScaleDownBehavior: "TERMINATE_AT_TASK_COMPLETION"
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
- Key: "for-use-with-amazon-emr-managed-policies"
  Value: "true"
