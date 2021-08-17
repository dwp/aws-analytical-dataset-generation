---
BootstrapActions:
- Name: "download_scripts"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/download_scripts.sh"
- Name: "start_ssm"
  ScriptBootstrapAction:
    Path: "file:/var/ci/start_ssm.sh"
- Name: "metadata"
  ScriptBootstrapAction:
    Path: "file:/var/ci/metadata.sh"
- Name: "emr-setup"
  ScriptBootstrapAction:
    Path: "file:/var/ci/emr-setup.sh"
- Name: "installer"
  ScriptBootstrapAction:
    Path: "file:/var/ci/installer.sh"
- Name: "metrics-setup"
  ScriptBootstrapAction:
    Path: "file:/var/ci/metrics-setup.sh"
- Name: "hive-setup"
  ScriptBootstrapAction:
    Path: "file:/var/ci/hive-setup.sh"
Steps:
- Name: "courtesy-flush"
  HadoopJarStep:
    Args:
    - "file:/var/ci/courtesy-flush.sh"
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
- Name: "send_notification"
  HadoopJarStep:
    Args:
    - "python3"
    - "/opt/emr/send_notification.py"
    Jar: "command-runner.jar"
  ActionOnFailure: "${action_on_failure}"
- Name: "flush-pushgateway"
  HadoopJarStep:
    Args:
    - "file:/var/ci/flush-pushgateway.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "CONTINUE"


aws emr cancel-steps --cluster-id j-1Z0PR30KRWB9S --step-ids "s-E650PUGGFFKR" "s-1O3IP7RQSDEO4" "s-3OUP70O1UWHW" "s-ZUY9MF8K1DUA" --profile dataworks-development
aws emr add-steps --cluster-id j-1Z0PR30KRWB9S --steps '[{"Name": "DW-6788", "ActionOnFailure": "CONTINUE", "Jar": "command-runner.jar", "Args": ["python3", "/opt/emr/generate_dataset_from_historical_equality.py", "--s3_prefix", "equalities", "--start_date", "2014-11-25", "--end_date", "2014-11-25"]}]' --profile dataworks-development



{
        "Name": DW-6788,
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": ["python3", "/opt/emr/generate_dataset_from_historical_equality.py", "--s3_prefix", "equalities"]
        }
}


'[{"Name": "DW-6788", "ActionOnFailure": "CONTINUE", "Jar": "command-runner.jar", "Args": ["python3", "/opt/emr/generate_dataset_from_historical_equality.py", "--s3_prefix", "equalities", "--start_date", "2014-11-25", "--end_date", "2014-11-25"]}]'