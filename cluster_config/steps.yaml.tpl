---
BootstrapActions:
- Name: "run-log4j-patch"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/patch-log4j-emr-6.3.1-v2.sh"
- Name: "download_scripts"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/download_scripts.sh"
- Name: "start_ssm"
  ScriptBootstrapAction:
    Path: "file:/var/ci/start_ssm.sh"
- Name: "metadata"
  ScriptBootstrapAction:
    Path: "file:/var/ci/metadata.sh"
- Name: "config_hcs"
  ScriptBootstrapAction:
    Path: "file:/var/ci/config_hcs.sh"
    Args: [
      "${environment}",
      "${proxy_http_host}",
      "${proxy_http_port}",
      "${tanium_server_1}",
      "${tanium_server_2}",
      "${tanium_env}",
      "${tanium_port}",
      "${tanium_log_level}",
      "${install_tenable}",
      "${install_trend}",
      "${install_tanium}",
      "${tenantid}",
      "${token}",
      "${policyid}",
      "${tenant}"
    ]
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
- Name: "equalities-managed"
  HadoopJarStep:
    Args:
    - "file:/var/ci/equalities-managed.sh"
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
