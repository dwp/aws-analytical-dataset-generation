resource "aws_s3_bucket_object" "create-hive-tables" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/create-hive-tables.py"
  content = templatefile("${path.module}/steps/create-hive-tables.py",
    {
      bucket      = aws_s3_bucket.published.id
      secret_name = local.secret_name
      log_path    = "/var/log/adg/hive-tables-creation.log"
    }
  )
}

resource "aws_s3_bucket_object" "generate_analytical_dataset_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_analytical_dataset.py"
  content = templatefile("${path.module}/steps/generate_analytical_dataset.py",
    {
      secret_name        = local.secret_name
      staging_db         = "analytical_dataset_generation_staging"
      published_db       = "analytical_dataset_generation"
      file_location      = "analytical-dataset"
      url                = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
      aws_default_region = "eu-west-2"
      log_path           = "/var/log/adg/generate-analytical-dataset.log"
    }
  )
}

resource "aws_s3_bucket_object" "generate_dataset_from_htme_script" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/generate_dataset_from_htme.py"
  content = templatefile("${path.module}/steps/generate_dataset_from_htme.py",
  {
    secret_name        = local.secret_name
    published_db       = "analytical_dataset_generation"
    file_location      = "analytical-dataset"
    url                = format("%s/datakey/actions/decrypt", data.terraform_remote_state.crypto.outputs.dks_endpoint[local.environment])
    aws_default_region = "eu-west-2"
    log_path           = "/var/log/adg/generate-analytical-dataset.log"
    s3_prefix          = "businessdata/mongo/ucdata/2020-07-26/full/"
  }
  )
}

resource "aws_s3_bucket_object" "hive_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/hive-setup.sh"
  content = templatefile("${path.module}/steps/hive-setup.sh",
    {
      hive-scripts-path           = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.create-hive-tables.key)
      python_logger               = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.logger.key)
      generate_analytical_dataset = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.generate_dataset_from_htme_script.key)
    }
  )
}

resource "aws_s3_bucket_object" "logger" {
  bucket  = data.terraform_remote_state.common.outputs.config_bucket.id
  key     = "component/analytical-dataset-generation/logger.py"
  content = file("${path.module}/steps/logger.py")
}

resource "aws_s3_bucket_object" "metrics_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key    = "component/analytical-dataset-generation/metrics-setup.sh"
  content = templatefile("${path.module}/steps/metrics-setup.sh",
    {
      proxy_url                   = data.terraform_remote_state.internal_compute.outputs.internet_proxy.url
      metrics_properties          = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.metrics_properties.key)
      metrics_pom                 = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.metrics_pom.key)
    }
  )
}

resource "aws_s3_bucket_object" "metrics_properties" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key    = "component/analytical-dataset-generation/metrics/metrics.properties"
  content = templatefile("${path.module}/steps/metrics_config/metrics.properties",
    {
      adg_pushgateway_hostname = data.terraform_remote_state.metrics_infrastructure.outputs.adg_pushgateway_hostname
    }
  )
}

resource "aws_s3_bucket_object" "metrics_pom" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
  key    = "component/analytical-dataset-generation/metrics/pom.xml"
  content = file("${path.module}/steps/metrics_config/pom.xml")
}

