resource "aws_s3_bucket_object" "metadata_script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/metadata.sh"
  content    = file("${path.module}/bootstrap_actions/metadata.sh")
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "download_scripts_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/download_scripts.sh"
  content = templatefile("${path.module}/bootstrap_actions/download_scripts.sh",
    {
      VERSION                 = local.adg_version[local.environment]
      ADG_LOG_LEVEL           = local.adg_log_level[local.environment]
      ENVIRONMENT_NAME        = local.environment
      S3_COMMON_LOGGING_SHELL = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, data.terraform_remote_state.common.outputs.application_logging_common_file.s3_id)
      S3_LOGGING_SHELL        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logging_script.key)
      scripts_location        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, "component/analytical-dataset-generation")
  })
}

resource "aws_s3_bucket_object" "resume_step_script" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/resume_step.sh"
  content = file("${path.module}/bootstrap_actions/resume_step.sh")
}

resource "aws_s3_bucket_object" "emr_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/emr-setup.sh"
  content = templatefile("${path.module}/bootstrap_actions/emr-setup.sh",
    {
      ADG_LOG_LEVEL                   = local.adg_log_level[local.environment]
      CREATE_PDM_TRIGGER              = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.create_pdm_trigger_script.key)
      S3_SEND_SNS_NOTIFICATION        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.send_notification_script.key)
      RESUME_STEP_SHELL               = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.resume_step_script.key)
      aws_default_region              = "eu-west-2"
      full_proxy                      = data.terraform_remote_state.internal_compute.outputs.internet_proxy.url
      full_no_proxy                   = local.no_proxy
      acm_cert_arn                    = aws_acm_certificate.analytical-dataset-generator.arn
      private_key_alias               = "private_key"
      truststore_aliases              = join(",", var.truststore_aliases)
      truststore_certs                = "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/dataworks_root_ca.pem,s3://${data.terraform_remote_state.mgmt_ca.outputs.public_cert_bucket.id}/ca_certificates/dataworks/dataworks_root_ca.pem"
      dks_endpoint                    = data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment]
      cwa_metrics_collection_interval = local.cw_agent_metrics_collection_interval
      cwa_namespace                   = local.cw_agent_namespace
      cwa_log_group_name              = aws_cloudwatch_log_group.analytical_dataset_generator.name
      S3_CLOUDWATCH_SHELL             = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.cloudwatch_sh.key)
      cwa_bootstrap_loggrp_name       = aws_cloudwatch_log_group.adg_cw_bootstrap_loggroup.name
      cwa_steps_loggrp_name           = aws_cloudwatch_log_group.adg_cw_steps_loggroup.name
      cwa_tests_loggrp_name           = aws_cloudwatch_log_group.adg_cw_tests_loggroup.name
      cwa_yarnspark_loggrp_name       = aws_cloudwatch_log_group.adg_cw_yarnspark_loggroup.name
      name                            = local.emr_cluster_name
      publish_bucket_id               = data.terraform_remote_state.common.outputs.published_bucket.id
      update_dynamo_sh                = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.update_dynamo_sh.key)
      dynamo_schema_json              = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.dynamo_json_file.key)
  })
}

resource "aws_s3_bucket_object" "ssm_script" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/start_ssm.sh"
  content = file("${path.module}/bootstrap_actions/start_ssm.sh")
}

resource "aws_s3_bucket_object" "installer_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/installer.sh"
  content = templatefile("${path.module}/bootstrap_actions/installer.sh",
    {
      full_proxy    = data.terraform_remote_state.internal_compute.outputs.internet_proxy.url
      full_no_proxy = local.no_proxy
    }
  )
}

resource "aws_s3_bucket_object" "logging_script" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/logging.sh"
  content = file("${path.module}/bootstrap_actions/logging.sh")
}

resource "aws_cloudwatch_log_group" "analytical_dataset_generator" {
  name              = local.cw_agent_log_group_name
  retention_in_days = 180
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "adg_cw_bootstrap_loggroup" {
  name              = local.cw_agent_bootstrap_loggrp_name
  retention_in_days = 180
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "adg_cw_steps_loggroup" {
  name              = local.cw_agent_steps_loggrp_name
  retention_in_days = 180
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "adg_cw_yarnspark_loggroup" {
  name              = local.cw_agent_yarnspark_loggrp_name
  retention_in_days = 180
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "adg_cw_tests_loggroup" {
  name              = local.cw_agent_tests_loggrp_name
  retention_in_days = 180
  tags              = local.common_tags
}

resource "aws_s3_bucket_object" "cloudwatch_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/cloudwatch.sh"
  content = templatefile("${path.module}/bootstrap_actions/cloudwatch.sh",
    {
      emr_release = var.emr_release[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "metrics_setup_sh" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/metrics-setup.sh"
  content = templatefile("${path.module}/bootstrap_actions/metrics-setup.sh",
    {
      proxy_url          = data.terraform_remote_state.internal_compute.outputs.internet_proxy.url
      metrics_properties = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.metrics_properties.key)
      metrics_pom        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.metrics_pom.key)
      metrics_jar        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.metrics_jar.key)
      prometheus_config  = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.prometheus_config.key)
    }
  )
}

resource "aws_s3_bucket_object" "metrics_properties" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/metrics/metrics.properties"
  content = templatefile("${path.module}/bootstrap_actions/metrics_config/metrics.properties",
    {
      adg_pushgateway_hostname = data.terraform_remote_state.metrics_infrastructure.outputs.adg_pushgateway_hostname
    }
  )
}

resource "aws_s3_bucket_object" "metrics_pom" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/metrics/pom.xml"
  content    = file("${path.module}/bootstrap_actions/metrics_config/pom.xml")
}

resource "aws_s3_bucket_object" "prometheus_config" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/metrics/prometheus_config.yml"
  content    = file("${path.module}/bootstrap_actions/metrics_config/prometheus_config.yml")
}

resource "aws_s3_bucket_object" "metrics_jar" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/metrics/adg-exporter.jar"
  content    = filebase64("${var.analytical_dataset_generation_exporter_jar.base_path}/analytical-dataset-generation-exporter-${var.analytical_dataset_generation_exporter_jar.version}.jar")
}

resource "aws_s3_bucket_object" "download_sql_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/download_sql.sh"
  content = templatefile("${path.module}/bootstrap_actions/download_sql.sh",
    {
      version               = local.mongo_latest_version[local.environment]
      s3_artefact_bucket_id = data.terraform_remote_state.management_artefact.outputs.artefact_bucket.id
      adg_log_level         = local.adg_log_level[local.environment]
      environment_name      = local.environment
    }
  )
}

resource "aws_s3_bucket_object" "dynamo_json_file" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/dynamo_schema.json"
  content    = file("${path.module}/bootstrap_actions/dynamo_schema.json")
}

resource "aws_s3_bucket_object" "update_dynamo_sh" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/update_dynamo.sh"
  content = templatefile("${path.module}/bootstrap_actions/update_dynamo.sh",
    {
      dynamodb_table_name = local.data_pipeline_metadata
    }
  )
}

resource "aws_s3_bucket_object" "hive_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/hive-setup.sh"
  content = templatefile("${path.module}/bootstrap_actions/hive-setup.sh",
    {
      python_logger               = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logger.key)
      generate_analytical_dataset = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.generate_dataset_from_htme_script.key)
      python_resume_script        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.resume_step.key)
      published_db                = local.published_db
    }
  )
}
