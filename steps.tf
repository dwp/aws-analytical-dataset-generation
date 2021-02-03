resource "aws_s3_bucket_object" "generate_dataset_from_htme_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_dataset_from_htme.py"
  content = templatefile("${path.module}/steps/generate_dataset_from_htme.py",
    {
      secret_name            = local.secret_name
      published_db           = local.published_db
      hive_metastore_backend = local.hive_metastore_backend[local.environment]
      data_pipeline_metadata = local.data_pipeline_metadata
      file_location          = "analytical-dataset"
      url                    = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
      aws_default_region     = "eu-west-2"
      log_path               = "/var/log/adg/generate-analytical-dataset.log"
      s3_prefix              = var.htme_data_location[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "hive_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/hive-setup.sh"
  content = templatefile("${path.module}/steps/hive-setup.sh",
    {
      python_logger               = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logger.key)
      generate_analytical_dataset = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.generate_dataset_from_htme_script.key)
      published_db                = local.published_db
    }
  )
}

resource "aws_s3_bucket_object" "logger" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/logger.py"
  content = file("${path.module}/steps/logger.py")
}

resource "aws_s3_bucket_object" "send_notification_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/send_notification.py"
  content = templatefile("${path.module}/steps/send_notification.py",
    {
      publish_bucket   = data.terraform_remote_state.common.outputs.published_bucket.id
      status_topic_arn = aws_sns_topic.adg_completion_status_sns.arn
      log_path         = "/var/log/adg/adg_params.log"
    }
  )
}

resource "aws_s3_bucket_object" "flush_pushgateway" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key        = "component/analytical-dataset-generation/flush-pushgateway.sh"
  content = templatefile("${path.module}/steps/flush-pushgateway.sh",
    {
      adg_pushgateway_hostname = data.terraform_remote_state.metrics_infrastructure.outputs.adg_pushgateway_hostname
    }
  )
}
