resource "aws_emr_security_configuration" "ebs_emrfs_em" {
  name          = "adg_ebs_emrfs"
  configuration = jsonencode(local.ebs_emrfs_em)
}

resource "aws_s3_bucket_object" "cluster" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/cluster.yaml"
  content = templatefile("${path.module}/cluster_config/cluster.yaml.tpl",
    {
      s3_log_bucket          = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_log_prefix          = local.s3_log_prefix
      ami_id                 = var.emr_ami_id
      service_role           = aws_iam_role.adg_emr_service.arn
      instance_profile       = aws_iam_instance_profile.analytical_dataset_generator.arn
      security_configuration = aws_emr_security_configuration.ebs_emrfs_em.id
      emr_release            = var.emr_release[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "instances" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/instances.yaml"
  content = templatefile("${path.module}/cluster_config/instances.yaml.tpl",
    {
      keep_cluster_alive  = local.keep_cluster_alive[local.environment]
      add_master_sg       = aws_security_group.adg_common.id
      add_slave_sg        = aws_security_group.adg_common.id
      subnet_ids          = join(",", data.terraform_remote_state.internal_compute.outputs.adg_subnet.ids)
      master_sg           = aws_security_group.adg_master.id
      slave_sg            = aws_security_group.adg_slave.id
      service_access_sg   = aws_security_group.adg_emr_service.id
      instance_type       = var.emr_instance_type[local.environment]
      core_instance_count = var.emr_core_instance_count[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "steps" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/steps.yaml"
  content = templatefile("${path.module}/cluster_config/steps.yaml.tpl",
    {
      s3_config_bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
      action_on_failure = local.step_fail_action[local.environment]
    }
  )
}

# See https://aws.amazon.com/blogs/big-data/best-practices-for-successfully-managing-memory-for-apache-spark-applications-on-amazon-emr/
locals {
  spark_num_executors_per_instance = {
    development = 3 # 8 cores (minus one) for m5.24xlarge / 2 executors per core
    qa          = 3
    integration = 3
    preprod     = 3
    production  = 19 # 96 cores (minus one) for m5.24xlarge / 5 executors per core
  }
  spark_executor_total_memory = floor(var.emr_yarn_memory_gb_per_core_instance[local.environment] / local.spark_num_executors_per_instance)
  spark_executor_cores = {
    development = 2
    qa          = 2
    integration = 2
    preprod     = 2
    production  = 5 # Recommended on the link above
  }
  spark_executor_memory = {
    development = 10
    qa          = 10
    integration = 10
    preprod     = 10
    production  = 18 # 19 executors per instance for 24xlarge works out as this split of RAM each x 0.9
  }
  spark_yarn_executor_memory_overhead = {
    development = 2
    qa          = 2
    integration = 2
    preprod     = 2
    production  = 2 # 0.1 of the 20 per executor
  }
  spark_driver_memory = {
    development = 10
    qa          = 10
    integration = 10
    preprod     = 10
    production  = 18 # Same as executor memory
  }
  spark_driver_cores = {
    development = 2
    qa          = 2
    integration = 2
    preprod     = 2
    production  = 5 # Same as executor cores
  }
  spark_executor_instances  = var.spark_executor_instances[local.environment]
  spark_default_parallelism = local.spark_executor_instances * local.spark_executor_cores * 2
  spark_kyro_buffer         = var.spark_kyro_buffer[local.environment]
}

resource "aws_s3_bucket_object" "configurations" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/configurations.yaml"
  content = templatefile("${path.module}/cluster_config/configurations.yaml.tpl",
    {
      s3_log_bucket                       = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_log_prefix                       = local.s3_log_prefix
      s3_published_bucket                 = data.terraform_remote_state.common.outputs.published_bucket.id
      s3_ingest_bucket                    = data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket
      hbase_root_path                     = local.hbase_root_path
      proxy_no_proxy                      = replace(replace(local.no_proxy, ",", "|"), ".s3", "*.s3")
      proxy_http_host                     = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_http_port                     = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      proxy_https_host                    = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_https_port                    = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      emrfs_metadata_tablename            = local.emrfs_metadata_tablename
      s3_htme_bucket                      = data.terraform_remote_state.ingest.outputs.s3_buckets.htme_bucket
      spark_executor_cores                = local.spark_executor_cores[local.environment]
      spark_executor_memory               = local.spark_executor_memory[local.environment]
      spark_yarn_executor_memory_overhead = local.spark_yarn_executor_memory_overhead[local.environment]
      spark_driver_memory                 = local.spark_driver_memory[local.environment]
      spark_driver_cores                  = local.spark_driver_cores[local.environment]
      spark_executor_instances            = local.spark_executor_instances
      spark_default_parallelism           = local.spark_default_parallelism
      spark_kyro_buffer                   = local.spark_kyro_buffer
      hive_metsatore_username             = var.metadata_store_adg_writer_username
      hive_metastore_pwd                  = aws_secretsmanager_secret.metadata_store_adg_writer.name
      hive_metastore_endpoint             = aws_rds_cluster.hive_metastore.endpoint
      hive_metastore_database_name        = aws_rds_cluster.hive_metastore.database_name
      hive_metastore_backend              = local.hive_metastore_backend[local.environment]
    }
  )
}

