---
Steps:
- Name: "emr-setup"
  HadoopJarStep:
    Args:
    - "s3://${s3_config_bucket}/component/emr-setup.sh"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "CONTINUE"
- Name: "copy-hbase-configuration"
  HadoopJarStep:
    Args:
    - "bash"
    - "-c"
    - "sudo cp /etc/hbase/conf/hbase-site.xml /etc/spark/conf/"
    Jar: "command-runner.jar"
  ActionOnFailure: "CONTINUE"
- Name: "submit-job"
  HadoopJarStep:
    Args:
    - "spark-submit"
    - "s3://${s3_config_bucket}/component/analytical-dataset-generation/generate-analytical-dataset.py"
    - "--deploy-mode"
    - "cluster"
    - "--master"
    - "yarn"
    - "--conf"
    - "spark.yarn.submit.waitAppCompletion=true"
    Jar: "command-runner.jar"
  ActionOnFailure: "CONTINUE"
