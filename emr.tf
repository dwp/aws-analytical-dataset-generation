resource "aws_emr_cluster" "cluster" {
  name                              = local.emr_cluster_name
  release_label                     = var.emr_release_label
  applications                      = var.emr_applications
  termination_protection            = var.termination_protection
  keep_job_flow_alive_when_no_steps = var.keep_flow_alive
  //TODO The below is need for transparent encryption/decryption when insecure DKS is set up
  //security_configuration            = aws_emr_security_configuration.emrfs_em.id
  service_role         = aws_iam_role.analytical_dataset_generator.arn
  log_uri              = format("s3n://%s/logs/", data.terraform_remote_state.security-tools.outputs.logstore_bucket.id)
  ebs_root_volume_size = local.ebs_root_volume_size
  //TODO Does this cluster autoscales?
  //autoscaling_role                  = aws_iam_role.emr_autoscaling_role.arn
  tags = merge({ "Name" = local.emr_cluster_name, "SSMEnabled" = "True" }, local.common_tags)
  //TODO the below needs to be replaced with DW-EMR-AMI
  custom_ami_id = "ami-0793487e5844edda0"

  ec2_attributes {
    subnet_id                         = data.terraform_remote_state.internal_compute.outputs.htme_subnet.ids[0]
    additional_master_security_groups = aws_security_group.analytical_dataset_generation.id
    additional_slave_security_groups  = aws_security_group.analytical_dataset_generation.id
    instance_profile                  = aws_iam_instance_profile.analytical_dataset_generator.arn
  }

  master_instance_group {
    name           = "MASTER"
    instance_count = 1
    instance_type  = local.master_instance_type
    ebs_config {
      size                 = local.ebs_config_size
      type                 = local.ebs_config_type
      iops                 = 0
      volumes_per_instance = local.ebs_config_volumes_per_instance
    }
  }

  core_instance_group {
    name           = "CORE"
    instance_count = local.core_instance_count
    instance_type  = local.core_instance_type
    ebs_config {
      size                 = local.ebs_config_size
      type                 = local.ebs_config_type
      iops                 = 0
      volumes_per_instance = local.ebs_config_volumes_per_instance
    }
  }

  // TODO use templated proxy env vars
  configurations_json = templatefile(format("%s/configuration.json", path.module), {
    logs_bucket_path = format("s3://%s/logs", data.terraform_remote_state.security-tools.outputs.logstore_bucket.id)
    data_bucket_path = format("s3://%s/data", aws_s3_bucket.published.id)
    //TODO this path needs to be taken from the output of aws-ingestion
    hbase_root_path    = format("s3://%s/business-data/single-topic-per-table-hbase", data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket)
    hive_external_path = format("s3://%s/analytical-dataset/hive/external", aws_s3_bucket.published.id)
    proxy_host         = data.terraform_remote_state.internet_egress.outputs.internet_proxy.dns_name
  })

  step {
    name              = "emr-setup"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
      jar = "s3://eu-west-2.elasticmapreduce/libs/script-runner/script-runner.jar"
      args = [
        format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.emr_setup_sh.key)
      ]
    }
  }

  step {
    name              = "copy-hbase-configuration"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
      jar = "command-runner.jar"
      args = [
        "bash",
        "-c",
        "sudo cp /etc/hbase/conf/hbase-site.xml /etc/spark/conf/"
      ]
    }
  }

  step {
    name              = "submit-job"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
      jar = "command-runner.jar"
      args = [
        "spark-submit",
        format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.generate-analytical-dataset-script.key),
        "--deploy-mode",
        "cluster",
        "--master",
        "yarn",
        "--conf",
        "spark.yarn.submit.waitAppCompletion=true"
      ]
    }
  }

  depends_on = [
    aws_s3_bucket_object.generate-analytical-dataset-script
  ]

  lifecycle {
    ignore_changes = [
      instance_group,
      ec2_attributes
    ]
  }
}
