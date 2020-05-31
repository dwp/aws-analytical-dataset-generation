---
BootstrapActions:
- Name: "setup-cluster"
  ScriptBootstrapAction:
    Path: "s3://${aws_s3_bucket_object.emr_setup_sh.bucket}/${aws_s3_bucket_object.emr_setup_sh.key}"
Steps:
- Name: "hive-setup"
  HadoopJarStep:
    Args:
    - "s3://${aws_s3_bucket_object.hive_setup_sh.bucket}/${aws_s3_bucket_object.hive_setup_sh.key}"
    Jar: "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
  ActionOnFailure: "CONTINUE"
- Name: "submit-job"
  HadoopJarStep:
    Args:
    - "spark-submit"
    - "s3://${aws_s3_bucket_object.generate_analytical_dataset_script.bucket}/${aws_s3_bucket_object.generate_analytical_dataset_script.key}"
    - "--deploy-mode"
    - "cluster"
    - "--master"
    - "yarn"
    - "--conf"
    - "spark.yarn.submit.waitAppCompletion=true"
    Jar: "command-runner.jar"
  ActionOnFailure: "CONTINUE"
