resource "aws_emr_security_configuration" "ebs_emrfs_em" {
  name          = "adg_ebs_emrfs"
  configuration = jsonencode(local.ebs_emrfs_em)
}

#TODO remove this
output "security_configuration" {
  value = aws_emr_security_configuration.ebs_emrfs_em
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
      keep_cluster_alive                  = local.keep_cluster_alive[local.environment]
      add_master_sg                       = aws_security_group.adg_common.id
      add_slave_sg                        = aws_security_group.adg_common.id
      subnet_ids                          = data.terraform_remote_state.internal_compute.outputs.adg_subnet_new.subnets.*.id
      master_sg                           = aws_security_group.adg_master.id
      slave_sg                            = aws_security_group.adg_slave.id
      service_access_sg                   = aws_security_group.adg_emr_service.id
      instance_type_core_one              = var.emr_instance_type_core_one[local.environment]
      instance_type_master                = var.emr_instance_type_master[local.environment]
      core_instance_count                 = var.emr_core_instance_count[local.environment]
      capacity_reservation_preference     = local.emr_capacity_reservation_preference
      capacity_reservation_usage_strategy = local.emr_capacity_reservation_usage_strategy
    }
  )
}

resource "aws_s3_bucket_object" "instances_incremental" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/instances_incremental.yaml"
  content = templatefile("${path.module}/cluster_config/instances_incremental.yaml.tpl",
    {
      keep_cluster_alive       = local.keep_cluster_alive[local.environment]
      add_master_sg            = aws_security_group.adg_common.id
      add_slave_sg             = aws_security_group.adg_common.id
      subnet_id                = data.terraform_remote_state.internal_compute.outputs.adg_subnet_new.subnets[index(data.terraform_remote_state.internal_compute.outputs.adg_subnet_new.subnets.*.availability_zone, local.emr_subnet_non_capacity_reserved_environments)].id
      master_sg                = aws_security_group.adg_master.id
      slave_sg                 = aws_security_group.adg_slave.id
      service_access_sg        = aws_security_group.adg_emr_service.id
      instance_type_core_one   = var.emr_instance_type_core_one_incremental[local.environment]
      instance_type_core_two   = var.emr_instance_type_core_two_incremental[local.environment]
      instance_type_core_three = var.emr_instance_type_core_three_incremental[local.environment]
      instance_type_master_one = var.emr_instance_type_master_one_incremental[local.environment]
      instance_type_master_two = var.emr_instance_type_master_two_incremental[local.environment]
      core_instance_count      = var.emr_core_instance_count_incremental[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "steps" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/steps.yaml"
  content = templatefile("${path.module}/cluster_config/steps.yaml.tpl",
    {
      s3_config_bucket    = data.terraform_remote_state.common.outputs.config_bucket.id
      action_on_failure   = local.step_fail_action[local.environment]
      s3_published_bucket = data.terraform_remote_state.common.outputs.published_bucket.id
      environment         = local.hcs_environment[local.environment]
      proxy_http_host     = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_http_port     = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
    }
  )
}

resource "aws_s3_bucket_object" "configurations" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/configurations.yaml"
  content = templatefile("${path.module}/cluster_config/configurations.yaml.tpl",
    {
      s3_log_bucket                                 = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_log_prefix                                 = local.s3_log_prefix
      s3_published_bucket                           = data.terraform_remote_state.common.outputs.published_bucket.id
      proxy_no_proxy                                = replace(replace(local.no_proxy, ",", "|"), ".s3", "*.s3")
      proxy_http_host                               = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_http_port                               = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      proxy_https_host                              = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_https_port                              = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      s3_htme_bucket                                = data.terraform_remote_state.internal_compute.outputs.htme_s3_bucket.id
      spark_kyro_buffer                             = local.spark_kyro_buffer
      hive_metsatore_username                       = data.terraform_remote_state.internal_compute.outputs.metadata_store_users.adg_writer.username
      hive_metastore_pwd                            = data.terraform_remote_state.internal_compute.outputs.metadata_store_users.adg_writer.secret_name
      hive_metastore_endpoint                       = data.terraform_remote_state.internal_compute.outputs.hive_metastore_v2.endpoint
      hive_metastore_database_name                  = data.terraform_remote_state.internal_compute.outputs.hive_metastore_v2.database_name
      hive_metastore_backend                        = local.hive_metastore_backend[local.environment]
      spark_executor_cores                          = local.spark_executor_cores[local.environment]
      spark_executor_memory                         = local.spark_executor_memory[local.environment]
      spark_yarn_executor_memory_overhead           = local.spark_yarn_executor_memory_overhead[local.environment]
      spark_driver_memory                           = local.spark_driver_memory[local.environment]
      spark_driver_cores                            = local.spark_driver_cores[local.environment]
      spark_executor_instances                      = local.spark_executor_instances
      spark_default_parallelism                     = local.spark_default_parallelism
      environment                                   = local.environment
      hive_tez_container_size                       = local.hive_tez_container_size[local.environment]
      hive_tez_java_opts                            = local.hive_tez_java_opts[local.environment]
      hive_auto_convert_join_noconditionaltask_size = local.hive_auto_convert_join_noconditionaltask_size[local.environment]
      tez_grouping_min_size                         = local.tez_grouping_min_size[local.environment]
      tez_grouping_max_size                         = local.tez_grouping_max_size[local.environment]
      tez_am_resource_memory_mb                     = local.tez_am_resource_memory_mb[local.environment]
      tez_am_launch_cmd_opts                        = local.tez_am_launch_cmd_opts[local.environment]
      tez_runtime_io_sort_mb                        = local.tez_runtime_io_sort_mb[local.environment]
      tez_runtime_unordered_output_buffer_size_mb   = local.tez_runtime_unordered_output_buffer_size_mb[local.environment]
      s3_historical_audit_bucket                    = data.terraform_remote_state.aws_ingestion.outputs.landed_write_light_bucket.bucket
      s3_historical_equality_bucket                 = data.terraform_remote_state.aws_ingestion.outputs.landed_write_light_bucket.bucket
    }
  )
}
