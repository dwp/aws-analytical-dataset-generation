resource "aws_s3_bucket_object" "emr_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/emr-setup.sh"
  content = templatefile("${path.module}/bootstrap_actions/emr-setup.sh",
    {
      VERSION                 = local.adg_version[local.environment]
      ADG_LOG_LEVEL           = local.adg_log_level[local.environment]
      ENVIRONMENT_NAME        = local.environment
      S3_COMMON_LOGGING_SHELL = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, data.terraform_remote_state.common.outputs.application_logging_common_file.s3_id)
      S3_LOGGING_SHELL        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logging_script.key)
      aws_default_region      = "eu-west-2"
      full_proxy              = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
      full_no_proxy           = local.no_proxy
      acm_cert_arn            = aws_acm_certificate.analytical-dataset-generator.arn
      private_key_alias       = "private_key"
      truststore_aliases      = join(",", var.truststore_aliases)
      truststore_certs        = "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/dataworks_root_ca.pem,s3://dw-management-dev-public-certificates/ca_certificates/dataworks/dataworks_root_ca.pem,s3://${local.env_certificate_bucket}/ca_certificates/dataworks/ca.pem,s3://dw-${local.management_account[local.environment]}-public-certificates/ca_certificates/dataworks/ca.pem,s3://${data.terraform_remote_state.mgmt_ca.outputs.public_cert_bucket.id}/ca_certificates/dataworks/root_ca.pem"
      dks_endpoint            = data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment]
      python_logger           = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logger.key)
  })
}

resource "aws_s3_bucket_object" "installer_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/installer.sh"
  content = templatefile("${path.module}/bootstrap_actions/installer.sh",
    {
      full_proxy    = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
      full_no_proxy = local.no_proxy
    }
  )
}

resource "aws_s3_bucket_object" "logging_script" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/logging.sh"
  content = file("${path.module}/bootstrap_actions/logging.sh")
}
