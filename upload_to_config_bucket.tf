resource "aws_s3_bucket_object" "generate_analytical_dataset_script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/generate_analytical_dataset.py"
  content    = data.template_file.analytical_dataset_generation_script.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "analytical_dataset_generation_script" {
  template = file(format("%s/generate_analytical_dataset.py", path.module))
  vars = {
    secret_name   = "ADG-Secret"
    staging_db    = "analytical_dataset_generation_staging"
    published_db  = "analytical_dataset_generation"
    file_location = "analytical-dataset"
    url           = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
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
    hbase_root_path = local.hbase_root_path
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
  }
}

resource "aws_s3_bucket_object" "meta_cleaner_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/meta-cleaner.sh"
  content = data.template_file.meta_cleaner_sh.rendered
}
data "template_file" "meta_cleaner_sh" {
  template = file(format("%s/meta-cleaner.sh", path.module))
  vars = {
    hbase_meta     = local.hbase_root_path
    metatable_name = local.dynamo_meta_name
  }
}


resource "aws_s3_bucket_object" "installer_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/installer.sh"
  content = data.template_file.installer_sh.rendered
}
data "template_file" "installer_sh" {
  template = file(format("%s/installer.sh", path.module))
  vars = {
    full_proxy    = data.terraform_remote_state.internet_egress.outputs.internet_proxy.http_address
    full_no_proxy = "127.0.0.1,localhost,169.254.169.254,*.s3.eu-west-2.amazonaws.com,s3.eu-west-2.amazonaws.com,sns.eu-west-2.amazonaws.com,sqs.eu-west-2.amazonaws.com,eu-west-2.queue.amazonaws.com,glue.eu-west-2.amazonaws.com,sts.eu-west-2.amazonaws.com,*.eu-west-2.compute.internal,dynamodb.eu-west-2.amazonaws.com"
  }
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
    bucket = aws_s3_bucket.published.id
  }
}

resource "aws_s3_bucket_object" "hive_setup_sh" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/hive-setup.sh"
  content = data.template_file.hive_setup_sh.rendered
}

data "template_file" "hive_setup_sh" {
  template = file(format("%s/hive-setup.sh", path.module))
  vars = {

    hive-scripts-path = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.create-hive-tables.key)
    collections_list  = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.collections_csv.key)
  }
}


resource "aws_s3_bucket_object" "collections_csv" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/collections.csv"
  content = data.template_file.collections_csv.rendered
}
data "template_file" "collections_csv" {
  template = file(format("%s/collections.csv", path.module))
  vars = {
  }
}


data "local_file" "logging_script" {
  filename = "logging.sh"
}

resource "aws_s3_bucket_object" "logging_script" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/logging.sh"
  content    = data.local_file.logging_script.content
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

