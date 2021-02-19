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
- Name: "metrics-setup"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/metrics-setup.sh"
- Name: "download-mongo-latest-sql"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/download_sql.sh"
Steps:
- Name: "courtesy-flush"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/courtesy-flush.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "hive-setup"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/hive-setup.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "create-mongo-latest-dbs"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/create-mongo-latest-dbs.sh"
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
- Name: "build-day-1-ContractClaimant"
  HadoopJarStep:
    Args:
    - "/opt/emr/aws-mongo-latest/update/executeUpdateContractClaimant.sh"
    - "${s3_published_bucket}"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: CONTINUE
- Name: "build-day-1-ToDo"
  HadoopJarStep:
    Args:
    - "/opt/emr/aws-mongo-latest/update/executeUpdateToDo.sh"
    - "${s3_published_bucket}"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: CONTINUE
- Name: "build-day-1-Statement"
  HadoopJarStep:
    Args:
    - "/opt/emr/aws-mongo-latest/update/executeUpdateStatement.sh"
    - "${s3_published_bucket}"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "${action_on_failure}"
