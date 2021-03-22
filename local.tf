locals {
  emr_cluster_name         = "aws-analytical-dataset-generator"
  hbase_root_path          = format("s3://%s", data.terraform_remote_state.ingest.outputs.s3_buckets.hbase_rootdir)
  secret_name_full         = "/concourse/dataworks/adg/fulls"
  secret_name_incremental  = "/concourse/dataworks/adg/incrementals"
  pdm_lambda_launcher_name = "pdm_cw_emr_launcher"
  pdm_lambda_cw_trigger    = "${local.pdm_lambda_launcher_name}-scheduled-rule"
  common_tags = {
    Environment  = local.environment
    Application  = local.emr_cluster_name
    CreatedBy    = "terraform"
    Owner        = "dataworks platform"
    Persistence  = "Ignore"
    AutoShutdown = "False"
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

  adg_emr_lambda_schedule = {
    development = "1 0 * * ? 2099"
    qa          = "1 0 * * ? *"
    integration = "00 14 6 Jul ? 2020" # trigger one off temp increase for DW-4437 testing
    preprod     = "1 0 * * ? *"
    production  = "1 0 * * ? 2025"
  }

  pdm_cw_emr_lambda_schedule = {
    development = "01 12 * * ? 2099"
    qa          = "00 15 * * ? 2099"
    integration = "00 15 * * ? 2099"
    preprod     = "00 15 * * ? 2099"
    production  = "00 15 * * ? *"
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
    development = "5.7.mysql_aurora.2.08.2"
    qa          = "5.7.mysql_aurora.2.08.2"
    integration = "5.7.mysql_aurora.2.08.2"
    preprod     = "5.7.mysql_aurora.2.08.2"
    production  = "5.7.mysql_aurora.2.08.2"
  }

  amazon_region_domain = "${data.aws_region.current.name}.amazonaws.com"
  endpoint_services    = ["dynamodb", "ec2", "ec2messages", "glue", "kms", "logs", "monitoring", ".s3", "s3", "secretsmanager", "ssm", "ssmmessages"]
  no_proxy             = "169.254.169.254,${join(",", formatlist("%s.%s", local.endpoint_services, local.amazon_region_domain))},${data.terraform_remote_state.metrics_infrastructure.outputs.adg_pushgateway_hostname}"

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
  cw_agent_metrics_collection_interval = 60

  s3_log_prefix          = "emr/analytical_dataset_generator"
  data_pipeline_metadata = data.terraform_remote_state.internal_compute.outputs.data_pipeline_metadata_dynamo.name

  published_nonsensitive_prefix = "runmetadata"
  hive_metastore_instance_type = {
    development = "db.t3.medium"
    qa          = "db.r5.large"
    integration = "db.t3.medium"
    preprod     = "db.t3.medium"
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
    preprod     = "200"
    production  = "unused"
  }

  hive_metastore_use_custom_max_connections = {
    development = true
    qa          = false
    integration = true
    preprod     = true
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

  hive_metastore_monitoring_interval = {
    development = 0
    qa          = 0
    integration = 0
    preprod     = 0
    production  = 0
  }

  hive_metastore_enable_perf_insights = {
    development = false
    qa          = true
    integration = false
    preprod     = false
    production  = true
  }

  adg_prefix = {
    development = "analytical-dataset"
    qa          = "analytical-dataset"
    integration = "analytical-dataset"
    preprod     = "analytical-dataset"
    production  = "analytical-dataset"
  }

  adg_retention_days = {
    development = 1
    qa          = 1
    integration = 1
    preprod     = 20
    production  = 20
  }

  mongo_latest_version = {
    development = "0.0.43"
    qa          = "0.0.43"
    integration = "0.0.43"
    preprod     = "0.0.43"
    production  = "0.0.43"
  }

  mongo_scripts_to_execute = {
    development = "executeUpdateStatement.sh"
    qa          = "executeUpdateStatement.sh"
    integration = "executeUpdateStatement.sh"
    preprod     = "executeUpdateStatement.sh"
    production  = "executeUpdateAll.sh"
  }

  skip_pdm_trigger_on_adg_completion = {
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
    preprod     = "true"
    production  = "false"
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
    preprod     = false
    production  = true
  }
}
