locals {

  emr_cluster_name         = "aws-analytical-dataset-generator"
  secret_name_full         = "/concourse/dataworks/adg/fulls"
  secret_name_incremental  = "/concourse/dataworks/adg/incrementals"
  pdm_lambda_launcher_name = "pdm_cw_emr_launcher"
  pdm_lambda_cw_trigger    = "${local.pdm_lambda_launcher_name}-scheduled-rule"
  common_emr_tags = merge(
    local.common_tags,
    {
      for-use-with-amazon-emr-managed-policies = "true"
    },
  )
  common_tags = {
    DWX_Environment = local.environment
    DWX_Application = local.emr_cluster_name
    Persistence     = "Ignore"
    AutoShutdown    = "False"
  }
  env_certificate_bucket = "dw-${local.environment}-public-certificates"
  dks_endpoint           = data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment]

  crypto_workspace = {
    management-dev = "management-dev"
    management     = "management"
  }

  management_workspace = {
    management-dev = "default"
    management     = "management"
  }

  management_account = {
    development = "management-dev"
    qa          = "management-dev"
    integration = "management-dev"
    preprod     = "management"
    production  = "management"
  }

  root_dns_name = {
    development = "dev.dataworks.dwp.gov.uk"
    qa          = "qa.dataworks.dwp.gov.uk"
    integration = "int.dataworks.dwp.gov.uk"
    preprod     = "pre.dataworks.dwp.gov.uk"
    production  = "dataworks.dwp.gov.uk"
  }

  adg_log_level = {
    development = "DEBUG"
    qa          = "DEBUG"
    integration = "DEBUG"
    preprod     = "INFO"
    production  = "INFO"
  }

  adg_version = {
    development = "0.0.1"
    qa          = "0.0.1"
    integration = "0.0.1"
    preprod     = "0.0.1"
    production  = "0.0.1"
  }

  emr_engine_version = {
    development = "5.7.mysql_aurora.2.11.2"
    qa          = "5.7.mysql_aurora.2.11.2"
    integration = "5.7.mysql_aurora.2.11.2"
    preprod     = "5.7.mysql_aurora.2.11.2"
    production  = "5.7.mysql_aurora.2.11.2"
  }

  amazon_region_domain = "${data.aws_region.current.name}.amazonaws.com"
  endpoint_services    = ["dynamodb", "ec2", "ec2messages", "glue", "kms", "logs", "monitoring", ".s3", "s3", "secretsmanager", "ssm", "ssmmessages"]
  no_proxy             = "169.254.169.254,${join(",", formatlist("%s.%s", local.endpoint_services, local.amazon_region_domain))},${local.adg_pushgateway_hostname}"

  ebs_emrfs_em = {
    EncryptionConfiguration = {
      EnableInTransitEncryption = false
      EnableAtRestEncryption    = true
      AtRestEncryptionConfiguration = {

        S3EncryptionConfiguration = {
          EncryptionMode             = "CSE-Custom"
          S3Object                   = "s3://${data.terraform_remote_state.management_artefact.outputs.artefact_bucket.id}/emr-encryption-materials-provider/encryption-materials-provider-all.jar"
          EncryptionKeyProviderClass = "uk.gov.dwp.dataworks.dks.encryptionmaterialsprovider.DKSEncryptionMaterialsProvider"
        }
        LocalDiskEncryptionConfiguration = {
          EnableEbsEncryption       = true
          EncryptionKeyProviderType = "AwsKms"
          AwsKmsKey                 = aws_kms_key.adg_ebs_cmk.arn
        }
      }
    }
  }

  keep_cluster_alive = {
    development = true
    qa          = false
    integration = false
    preprod     = false
    production  = false
  }

  step_fail_action = {
    development = "CONTINUE"
    qa          = "TERMINATE_CLUSTER"
    integration = "TERMINATE_CLUSTER"
    preprod     = "TERMINATE_CLUSTER"
    production  = "TERMINATE_CLUSTER"
  }

  cw_agent_namespace                   = "/app/analytical_dataset_generator"
  cw_agent_log_group_name              = "/app/analytical_dataset_generator"
  cw_agent_bootstrap_loggrp_name       = "/app/analytical_dataset_generator/bootstrap_actions"
  cw_agent_steps_loggrp_name           = "/app/analytical_dataset_generator/step_logs"
  cw_agent_yarnspark_loggrp_name       = "/app/analytical_dataset_generator/yarn-spark_logs"
  cw_agent_chrony_loggrp_name          = "/app/analytical_dataset_generator/chrony"
  cw_agent_tests_loggrp_name           = "/app/analytical_dataset_generator/tests_logs"
  cw_agent_metrics_collection_interval = 60

  s3_log_prefix                  = "emr/analytical_dataset_generator"
  data_pipeline_metadata         = data.terraform_remote_state.internal_compute.outputs.data_pipeline_metadata_dynamo.name
  uc_export_crown_dynamodb_table = data.terraform_remote_state.internal_compute.outputs.uc_export_crown_dynamodb_table.name

  published_nonsensitive_prefix = "runmetadata"
  hive_metastore_instance_type = {
    development = "db.t3.medium"
    qa          = "db.r5.large"
    integration = "db.t3.medium"
    preprod     = "db.r5.large"
    production  = "db.r5.large"
  }

  hive_metastore_instance_count = {
    development = length(data.aws_availability_zones.available.names)
    qa          = length(data.aws_availability_zones.available.names)
    integration = length(data.aws_availability_zones.available.names)
    preprod     = length(data.aws_availability_zones.available.names)
    production  = length(data.aws_availability_zones.available.names)
  }

  hive_metastore_custom_max_connections = {
    # Override default max_connections value which is set by a formula
    development = "200"
    qa          = "unused"
    integration = "200"
    preprod     = "unused"
    production  = "unused"
  }

  hive_metastore_use_custom_max_connections = {
    development = true
    qa          = false
    integration = true
    preprod     = false
    production  = false
  }

  published_db = "analytical_dataset_generation"

  hive_metastore_backend = {
    development = "aurora"
    qa          = "aurora"
    integration = "aurora"
    preprod     = "aurora"
    production  = "aurora"
  }

  hive_metastore_enable_perf_insights = {
    development = false
    qa          = true
    integration = false
    preprod     = true
    production  = true
  }

  mongo_latest_version = {
    development = "0.0.66"
    qa          = "0.0.66"
    integration = "0.0.66"
    preprod     = "0.0.66"
    production  = "0.0.64"
  }

  skip_pdm_trigger_on_adg_completion = {
    development = "true"
    qa          = "true"
    integration = "true"
    preprod     = "false"
    production  = "false"
  }

  skip_pdm_trigger_date_checks_on_adg_completion = {
    development = "true"
    qa          = "true"
    integration = "true"
    preprod     = "true"
    production  = "false"
  }

  skip_sns_notification_on_adg_completion = {
    development = "true"
    qa          = "true"
    integration = "true"
    preprod     = "false"
    production  = "false"
  }

  dynamodb_final_step = {
    development = local.skip_sns_notification_on_adg_completion[local.environment] == "true" ? "submit-job" : "send_notification"
    qa          = local.skip_sns_notification_on_adg_completion[local.environment] == "true" ? "submit-job" : "send_notification"
    integration = local.skip_sns_notification_on_adg_completion[local.environment] == "true" ? "submit-job" : "send_notification"
    preprod     = local.skip_sns_notification_on_adg_completion[local.environment] == "true" ? "submit-job" : "send_notification"
    production  = local.skip_sns_notification_on_adg_completion[local.environment] == "true" ? "submit-job" : "send_notification"
  }

  adg_max_retry_count = {
    development = "0"
    qa          = "0"
    integration = "0"
    preprod     = "0"
    production  = "2"
  }

  adg_alerts = {
    development = false
    qa          = false
    integration = false
    preprod     = true
    production  = true
  }

  hive_tez_container_size = {
    development = "2688"
    qa          = "2688"
    integration = "2688"
    preprod     = "2688"
    production  = "15360"
  }

  # 0.8 of hive_tez_container_size
  hive_tez_java_opts = {
    development = "-Xmx2150m"
    qa          = "-Xmx2150m"
    integration = "-Xmx2150m"
    preprod     = "-Xmx2150m"
    production  = "-Xmx12288m"
  }

  # 0.33 of hive_tez_container_size
  hive_auto_convert_join_noconditionaltask_size = {
    development = "896"
    qa          = "896"
    integration = "896"
    preprod     = "896"
    production  = "5068"
  }

  tez_runtime_unordered_output_buffer_size_mb = {
    development = "268"
    qa          = "268"
    integration = "268"
    preprod     = "268"
    production  = "2148"
  }

  # 0.4 of hive_tez_container_size
  tez_runtime_io_sort_mb = {
    development = "1075"
    qa          = "1075"
    integration = "1075"
    preprod     = "1075"
    production  = "6144"
  }

  tez_grouping_min_size = {
    development = "1342177"
    qa          = "1342177"
    integration = "1342177"
    preprod     = "1342177"
    production  = "52428800"
  }

  tez_grouping_max_size = {
    development = "268435456"
    qa          = "268435456"
    integration = "268435456"
    preprod     = "268435456"
    production  = "1073741824"
  }

  tez_am_resource_memory_mb = {
    development = "1024"
    qa          = "1024"
    integration = "1024"
    preprod     = "1024"
    production  = "12288"
  }

  # 0.8 of hive_tez_container_size
  tez_task_resource_memory_mb = {
    development = "1024"
    qa          = "1024"
    integration = "1024"
    preprod     = "1024"
    production  = "8196"
  }

  # 0.8 of tez_am_resource_memory_mb
  tez_am_launch_cmd_opts = {
    development = "-Xmx819m"
    qa          = "-Xmx819m"
    integration = "-Xmx819m"
    preprod     = "-Xmx819m"
    production  = "-Xmx6556m"
  }

  use_capacity_reservation = {
    development = false
    qa          = false
    integration = false
    preprod     = false
    production  = false
  }

  emr_capacity_reservation_preference     = local.use_capacity_reservation[local.environment] == true ? "open" : "none"
  emr_capacity_reservation_usage_strategy = local.use_capacity_reservation[local.environment] == true ? "use-capacity-reservations-first" : ""

  use_capacity_reservation_incremental = {
    development = false
    qa          = false
    integration = false
    preprod     = false
    production  = true
  }

  emr_capacity_reservation_preference_incremental     = local.use_capacity_reservation_incremental[local.environment] == true ? "open" : "none"
  emr_capacity_reservation_usage_strategy_incremental = local.use_capacity_reservation_incremental[local.environment] == true ? "use-capacity-reservations-first" : ""

  emr_subnet_non_capacity_reserved_environments = data.terraform_remote_state.common.outputs.aws_ec2_non_capacity_reservation_region

  pdm_start_do_not_run_after_hour = {
    development = "23" # 2300 (UTC) the day after the export as for lower environments we want to run on demand
    qa          = "23"
    integration = "23"
    preprod     = "23"
    production  = "02" # 0200 (UTC) the day after the export as would then interfere with next day's jobs
  }

  pdm_start_do_not_run_before_hour = {
    development = "00" # 0000 (UTC) the day of the export as for lower environments we want to run on demand
    qa          = "00"
    integration = "00"
    preprod     = "00"
    production  = "14" # 1400 (UTC) the day of the export as before would interfere with the working day's queries from users
  }

  # See https://aws.amazon.com/blogs/big-data/best-practices-for-successfully-managing-memory-for-apache-spark-applications-on-amazon-emr/
  spark_executor_cores = {
    development = 1
    qa          = 1
    integration = 1
    preprod     = 5
    production  = 1
  }

  spark_executor_memory = {
    development = 10
    qa          = 10
    integration = 10
    preprod     = 37
    production  = 35 # At least 20 or more per executor core
  }

  spark_yarn_executor_memory_overhead = {
    development = 2
    qa          = 2
    integration = 2
    preprod     = 5
    production  = 7
  }

  spark_driver_memory = {
    development = 5
    qa          = 5
    integration = 5
    preprod     = 37
    production  = 10 # Doesn't need as much as executors
  }

  spark_driver_cores = {
    development = 1
    qa          = 1
    integration = 1
    preprod     = 5
    production  = 1
  }

  yarn_nofile_limit = {
    development = 12345
    qa          = 32768
    integration = 32768
    preprod     = 65536
    production  = 65536
  }
  yarn_noproc_limit = {
    development = 12345
    qa          = 32768
    integration = 32768
    preprod     = 65536
    production  = 65536
  }
  spark_executor_instances  = var.spark_executor_instances[local.environment]
  spark_default_parallelism = local.spark_executor_instances * local.spark_executor_cores[local.environment] * 2
  spark_kyro_buffer         = var.spark_kyro_buffer[local.environment]

  adg_pushgateway_hostname = "${aws_service_discovery_service.adg_services.name}.${aws_service_discovery_private_dns_namespace.adg_services.name}"


  tenable_install = {
    development    = "true"
    qa             = "true"
    integration    = "true"
    preprod        = "true"
    production     = "true"
    management-dev = "true"
    management     = "true"
  }

  trend_install = {
    development    = "true"
    qa             = "true"
    integration    = "true"
    preprod        = "true"
    production     = "true"
    management-dev = "true"
    management     = "true"
  }

  tanium_install = {
    development    = "true"
    qa             = "true"
    integration    = "true"
    preprod        = "true"
    production     = "true"
    management-dev = "true"
    management     = "true"
  }


  ## Tanium config
  ## Tanium Servers
  tanium1 = jsondecode(data.aws_secretsmanager_secret_version.terraform_secrets.secret_binary).tanium[local.environment].server_1
  tanium2 = jsondecode(data.aws_secretsmanager_secret_version.terraform_secrets.secret_binary).tanium[local.environment].server_2

  ## Tanium Env Config
  tanium_env = {
    development    = "pre-prod"
    qa             = "prod"
    integration    = "prod"
    preprod        = "prod"
    production     = "prod"
    management-dev = "pre-prod"
    management     = "prod"
  }

  ## Tanium prefix list for TGW for Security Group rules
  tanium_prefix = {
    development    = [data.aws_ec2_managed_prefix_list.list.id]
    qa             = [data.aws_ec2_managed_prefix_list.list.id]
    integration    = [data.aws_ec2_managed_prefix_list.list.id]
    preprod        = [data.aws_ec2_managed_prefix_list.list.id]
    production     = [data.aws_ec2_managed_prefix_list.list.id]
    management-dev = [data.aws_ec2_managed_prefix_list.list.id]
    management     = [data.aws_ec2_managed_prefix_list.list.id]
  }

  tanium_log_level = {
    development    = "41"
    qa             = "41"
    integration    = "41"
    preprod        = "41"
    production     = "41"
    management-dev = "41"
    management     = "41"
  }

  ## Trend config
  tenant   = jsondecode(data.aws_secretsmanager_secret_version.terraform_secrets.secret_binary).trend.tenant
  tenantid = jsondecode(data.aws_secretsmanager_secret_version.terraform_secrets.secret_binary).trend.tenantid
  token    = jsondecode(data.aws_secretsmanager_secret_version.terraform_secrets.secret_binary).trend.token

  policy_id = {
    development    = "1651"
    qa             = "1651"
    integration    = "1651"
    preprod        = "1651"
    production     = "1651"
    management-dev = "1651"
    management     = "1651"
  }
}
