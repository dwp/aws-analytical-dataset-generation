---
BootstrapActions:
- Name: "start_ssm"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/start_ssm.sh"
- Name: "metadata"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/metadata.sh"
- Name: "get-dks-cert"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/emr-setup.sh"
- Name: "installer"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/installer.sh"
Steps:
- Name: "metrics-setup"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/metrics-setup.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "hive-setup"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/hive-setup.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "submit-job"
  HadoopJarStep:
    Args:
    - "spark-submit"
    - "--master"
    - "yarn"
    - "--conf"
    - "spark.yarn.submit.waitAppCompletion=true"
    - "/opt/emr/generate_dataset_from_htme.py"
    Jar: "command-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "sns-notification"
  HadoopJarStep:
    Args:
    - "python3"
    - "/opt/emr/send_notification.py"
    Jar: "command-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "flush-pushgateway"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/flush-pushgateway.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
