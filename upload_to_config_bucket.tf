resource "aws_s3_bucket_object" "generate-analytical-dataset-script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/generate-analytical-dataset.py"
  content    = data.template_file.analytical_dataset_generation_script.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "analytical_dataset_generation_script" {
  template = file(format("%s/generate-analytical-dataset.py", path.module))
  vars = {
    secret_name = "ADG-Payload"
  }
}

resource "aws_s3_bucket_object" "analytical_dataset_generator_cluster_payload" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/analytical-dataset-generator-cluster-payload.json"
  content    = data.template_file.analytical_dataset_generator_cluster_payload.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "analytical_dataset_generator_cluster_payload" {
  template = file(format("%s/aws-api-payload.json", path.module))
  vars = {
  }
}
resource "aws_s3_bucket_object" "emr_setup_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/emr-setup.sh"
  content = data.template_file.emr_setup_sh.rendered
}

data "template_file" "emr_setup_sh" {
  template = file(format("%s/emr-setup.sh", path.module))
  vars = {
    aws_default_region = "eu-west-2"
    full_proxy         = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
    full_no_proxy      = "127.0.0.1,localhost,169.254.169.254,*.s3.eu-west-2.amazonaws.com,s3.eu-west-2.amazonaws.com,sns.eu-west-2.amazonaws.com,sqs.eu-west-2.amazonaws.com,eu-west-2.queue.amazonaws.com,glue.eu-west-2.amazonaws.com,sts.eu-west-2.amazonaws.com,*.eu-west-2.compute.internal,dynamodb.eu-west-2.amazonaws.com"
    acm_cert_arn       = data.aws_acm_certificate.htme.arn
    private_key_alias  = "private_key"
    truststore_aliases = join(",", var.truststore_aliases)
    truststore_certs   = "s3://${local.env_certificate_bucket}/ca_certificates/dataworks/ca.pem,s3://dw-management-dev-public-certificates/ca_certificates/dataworks/ca.pem,s3://${data.terraform_remote_state.mgmt_ca.outputs.public_cert_bucket.id}/ca_certificates/dataworks/root_ca.pem",
    hive-scripts-path  = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.create-hive-tables.key)


    dks_endpoint = local.dks_endpoint
  }
}

// TODO Ticket created to replace this https://projects.ucd.gpn.gov.uk/browse/DW-3765
data "aws_acm_certificate" "htme" {
  domain = "htme.${local.root_dns_name[local.environment]}"
}

resource "aws_s3_bucket_object" "create-hive-tables" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/create-hive-tables.py"
  content    = data.template_file.create-hive-tables.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "create-hive-tables" {
  template = file(format("%s/hive-tables-creation.py", path.module))
  vars = {
    bucket     = aws_s3_bucket.published.id
  }
}
