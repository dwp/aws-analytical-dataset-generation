data "template_file" "emr_setup_sh" {
  template = file(format("%s/bootstrap_actions/emr-setup.sh", path.module))
  vars = {
    VERSION                 = local.adg_version[local.environment]
    ADG_LOG_LEVEL           = local.adg_log_level[local.environment]
    ENVIRONMENT_NAME        = local.environment
    S3_COMMON_LOGGING_SHELL = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, data.terraform_remote_state.common.outputs.application_logging_common_file.s3_id)
    S3_LOGGING_SHELL        = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logging_script.key)
    aws_default_region      = "eu-west-2"
    full_proxy              = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
    full_no_proxy           = "127.0.0.1,localhost,169.254.169.254,*.s3.eu-west-2.amazonaws.com,s3.eu-west-2.amazonaws.com,sns.eu-west-2.amazonaws.com,sqs.eu-west-2.amazonaws.com,eu-west-2.queue.amazonaws.com,glue.eu-west-2.amazonaws.com,sts.eu-west-2.amazonaws.com,*.eu-west-2.compute.internal,dynamodb.eu-west-2.amazonaws.com"
    acm_cert_arn            = aws_acm_certificate.analytical-dataset-generator.arn
    private_key_alias       = "private_key"
    truststore_aliases      = join(",", var.truststore_aliases)
    truststore_certs        = "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/dataworks_root_ca.pem,s3://dw-management-dev-public-certificates/ca_certificates/dataworks/dataworks_root_ca.pem,s3://${local.env_certificate_bucket}/ca_certificates/dataworks/ca.pem,s3://dw-${local.management_account[local.environment]}-public-certificates/ca_certificates/dataworks/ca.pem,s3://${data.terraform_remote_state.mgmt_ca.outputs.public_cert_bucket.id}/ca_certificates/dataworks/root_ca.pem"
    dks_endpoint            = data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment]
    python_logger           = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logger.key)
  }
}

resource "aws_s3_bucket_object" "emr_setup_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/emr-setup.sh"
  content = data.template_file.emr_setup_sh.rendered
}

data "template_file" "installer_sh" {
  template = file("bootstrap_actions/installer.sh")
  vars = {
    full_proxy    = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
    full_no_proxy = "127.0.0.1,localhost,169.254.169.254,*.s3.eu-west-2.amazonaws.com,s3.eu-west-2.amazonaws.com,sns.eu-west-2.amazonaws.com,sqs.eu-west-2.amazonaws.com,eu-west-2.queue.amazonaws.com,glue.eu-west-2.amazonaws.com,sts.eu-west-2.amazonaws.com,*.eu-west-2.compute.internal,dynamodb.eu-west-2.amazonaws.com"
  }
}

resource "aws_s3_bucket_object" "installer_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/installer.sh"
  content = data.template_file.installer_sh.rendered
}

data "local_file" "logging_script" {
  filename = "bootstrap_actions/logging.sh"
}

resource "aws_s3_bucket_object" "logging_script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/logging.sh"
  content    = data.local_file.logging_script.content
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}
