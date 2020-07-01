locals {
  emr_cluster_name                = "aws-analytical-dataset-generator"
  master_instance_type            = "m5.2xlarge"
  core_instance_type              = "m5.2xlarge"
  core_instance_count             = 1
  task_instance_type              = "m5.2xlarge"
  ebs_root_volume_size            = 100
  ebs_config_size                 = 250
  ebs_config_type                 = "gp2"
  ebs_config_volumes_per_instance = 1
  autoscaling_min_capacity        = 0
  autoscaling_max_capacity        = 5
  dks_port                        = 8443
  dynamo_meta_name                = "DataGen-metadata"
  hbase_root_path                 = format("s3://%s", data.terraform_remote_state.ingest.outputs.s3_buckets.hbase_rootdir)
  secret_name                     = "/concourse/dataworks/adg"
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
    development = "1 0 * * ? *"
    qa          = "1 0 * * ? *"
    integration = "00 17 1 Jul ? 2020" # trigger one off temp increase for DW-4437 testing
    preprod     = "1 0 * * ? *"
    production  = "1 0 * * ? 2025"
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

  amazon_region_domain = "${data.aws_region.current.name}.amazonaws.com"
  endpoint_services    = ["autoscaling", "dynamodb", "ec2", "ec2messages", "ecr.dkr", "glue", "kms", "logs", "monitoring", ".s3", "s3", "secretsmanager", "sns", "sqs", "ssm", "ssmmessages"]
  no_proxy             = "169.254.169.254,${join(",", formatlist("%s.%s", local.endpoint_services, local.amazon_region_domain))}"

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

  cw_agent_namespace                   = "/app/analytical_dataset_generator"
  cw_agent_log_group_name              = "/app/analytical_dataset_generator"
  cw_agent_bootstrap_loggrp_name       = "/app/analytical_dataset_generator/bootstrap_actions"
  cw_agent_steps_loggrp_name           = "/app/analytical_dataset_generator/step_logs"
  cw_agent_yarnspark_loggrp_name       = "/app/analytical_dataset_generator/yarn-spark_logs"
  cw_agent_metrics_collection_interval = 60

  s3_log_prefix            = "emr/analytical_dataset_generator"
  emrfs_metadata_tablename = "Analytical_Dataset_Generation_Metadata"
}
