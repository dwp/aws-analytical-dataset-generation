resource "aws_s3_bucket_object" "create-hive-tables" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/create-hive-tables.py"
  content = templatefile("${path.module}/steps/create-hive-tables.py",
    {
      bucket      = aws_s3_bucket.published.id
      secret_name = local.secret_name
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
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
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "hive_setup_sh" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "component/analytical-dataset-generation/hive-setup.sh"
  content = templatefile("${path.module}/steps/hive-setup.sh",
    {
      hive-scripts-path = format("s3://%s/%s", data.terraform_remote_state.common.outputs.config_bucket.id, aws_s3_bucket_object.create-hive-tables.key)
    }
  )
}

resource "aws_s3_bucket_object" "logger" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "component/analytical-dataset-generation/logger.py"
  content    = file("${path.module}/steps/logger.py")
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}
