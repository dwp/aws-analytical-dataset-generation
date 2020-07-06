---
BootstrapActions:
- Name: "get-dks-cert"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/emr-setup.sh"
- Name: "installer"
  ScriptBootstrapAction:
    Path: "s3://${s3_config_bucket}/component/analytical-dataset-generation/installer.sh"
Steps:
- Name: "hive-setup"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/hive-setup.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "CONTINUE"
- Name: "submit-job"
  HadoopJarStep:
    Args:
    - "spark-submit"
    - "/opt/emr/generate_analytical_dataset.py"
    - "--deploy-mode"
    - "cluster"
    - "--master"
    - "yarn"
    - "--conf"
    - "spark.yarn.submit.waitAppCompletion=true"
    - "--files"
    - "/etc/hbase/conf/hbase-site.xml"
    Jar: "command-runner.jar"
  ActionOnFailure: "CONTINUE"

