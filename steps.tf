resource "aws_s3_bucket_object" "generate_dataset_from_htme_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_dataset_from_htme.py"
  content = templatefile("${path.module}/steps/generate_dataset_from_htme.py",
    {
      secret_name_full        = local.secret_name_full
      secret_name_incremental = local.secret_name_incremental
      published_db            = local.published_db
      hive_metastore_backend  = local.hive_metastore_backend[local.environment]
      file_location           = "analytical-dataset"
      url                     = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
      aws_default_region      = "eu-west-2"
      log_path                = "/var/log/adg/generate-analytical-dataset.log"
      s3_prefix               = var.htme_data_location[local.environment]
      dynamodb_table_name     = local.uc_export_crown_dynamodb_table
      monitoring_topic_arn    = data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn
      data_pipeline_metadata  = local.data_pipeline_metadata
    }
  )
}

resource "aws_s3_bucket_object" "generate_dataset_from_historical_audit" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_dataset_from_historical_audit.py"
  content = templatefile("${path.module}/steps/generate_dataset_from_historical_audit.py",
    {
      published_db           = local.published_db
      hive_metastore_backend = local.hive_metastore_backend[local.environment]
      file_location          = "analytical-dataset"
      url                    = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
      aws_default_region     = "eu-west-2"
      log_path               = "/var/log/adg/generate-analytical-dataset-historical-audit.log"
      s3_prefix              = var.historical_audit_data_location[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "generate_dataset_from_historical_equality" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_dataset_from_historical_equality.py"
  content = templatefile("${path.module}/steps/generate_dataset_from_historical_equality.py",
    {
      published_db           = local.published_db
      hive_metastore_backend = local.hive_metastore_backend[local.environment]
      file_location          = "analytical-dataset"
      url                    = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
      aws_default_region     = "eu-west-2"
      log_path               = "/var/log/adg/generate-analytical-dataset-historical-equality.log"
      s3_prefix              = var.historical_equality_data_location[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "logger" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/logger.py"
  content = file("${path.module}/steps/logger.py")
}

resource "aws_s3_bucket_object" "resume_step" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/resume_step.py"
  content = file("${path.module}/steps/resume_step.py")
}

resource "aws_s3_bucket_object" "send_notification_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/send_notification.py"
  content = templatefile("${path.module}/steps/send_notification.py",
    {
      publish_bucket       = data.terraform_remote_state.common.outputs.published_bucket.id
      status_topic_arn     = aws_sns_topic.adg_completion_status_sns.arn
      log_path             = "/var/log/adg/sns_notification.log"
      s3_prefix            = var.htme_data_location[local.environment]
      skip_message_sending = local.skip_sns_notification_on_adg_completion[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "flush_pushgateway" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/flush-pushgateway.sh"
  content = templatefile("${path.module}/steps/flush-pushgateway.sh",
    {
      adg_pushgateway_hostname = local.adg_pushgateway_hostname
    }
  )
}

resource "aws_s3_bucket_object" "courtesy_flush" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/courtesy-flush.sh"
  content = templatefile("${path.module}/steps/courtesy-flush.sh",
    {
      adg_pushgateway_hostname = local.adg_pushgateway_hostname
    }
  )
}

resource "aws_s3_bucket_object" "equalities-managed" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/equalities-managed.sh"
  content = file("${path.module}/steps/equalities-managed.sh")
}
