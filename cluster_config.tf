resource "aws_s3_bucket_object" "cluster" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/cluster.yaml"
  content = templatefile("${path.module}/cluster_config/cluster.yaml.tpl",
    {
      s3_log_bucket    = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      ami_id           = var.emr_ami_id
      service_role     = aws_iam_role.analytical_dataset_generator.arn
      instance_profile = aws_iam_instance_profile.analytical_dataset_generator.arn
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "instances" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/instances.yaml"
  content = templatefile("${path.module}/cluster_config/instances.yaml.tpl",
    {
      add_master_sg     = aws_security_group.analytical_dataset_generation.id
      add_slave_sg      = aws_security_group.analytical_dataset_generation.id
      subnet_id         = data.terraform_remote_state.internal_compute.outputs.htme_subnet.ids[0]
      master_sg         = aws_security_group.master_sg.id
      slave_sg          = aws_security_group.slave_sg.id
      service_access_sg = aws_security_group.service_access_sg.id
      instance_type     = var.emr_instance_type[local.environment]
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "steps" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/steps.yaml"
  content = templatefile("${path.module}/cluster_config/steps.yaml.tpl",
    {
      s3_config_bucket = data.terraform_remote_state.common.outputs.config_bucket.id
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "configurations" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/configurations.yaml"
  content = templatefile("${path.module}/cluster_config/configurations.yaml.tpl",
    {
      s3_log_bucket       = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_published_bucket = aws_s3_bucket.published.id
      s3_ingest_bucket    = data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket
      hbase_root_path     = local.hbase_root_path
      proxy_no_proxy      = local.no_proxy
      proxy_http_address  = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.http_address
      proxy_https_address = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.https_address
    }
  )
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}
