resource "aws_emr_security_configuration" "ebs_emrfs_em" {
  name          = "adg_ebs_emrfs"
  configuration = jsonencode(local.ebs_emrfs_em)
}

resource "aws_s3_bucket_object" "cluster" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/cluster.yaml"
  content = templatefile("${path.module}/cluster_config/cluster.yaml.tpl",
    {
      s3_log_bucket          = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_log_prefix          = local.s3_log_prefix
      ami_id                 = var.emr_ami_id
      service_role           = aws_iam_role.adg_emr_service.arn
      instance_profile       = aws_iam_instance_profile.analytical_dataset_generator.arn
      security_configuration = aws_emr_security_configuration.ebs_emrfs_em.id
    }
  )
}

resource "aws_s3_bucket_object" "instances" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/instances.yaml"
  content = templatefile("${path.module}/cluster_config/instances.yaml.tpl",
    {
      keep_cluster_alive   = local.keep_cluster_alive[local.environment]
      add_master_sg        = aws_security_group.adg_common.id
      add_slave_sg         = aws_security_group.adg_common.id
      subnet_ids           = join(",", data.terraform_remote_state.internal_compute.outputs.adg_subnet.ids)
      master_sg            = aws_security_group.adg_master.id
      slave_sg             = aws_security_group.adg_slave.id
      service_access_sg    = aws_security_group.adg_emr_service.id
      instance_type        = var.emr_instance_type[local.environment]
      no_vcpus             = var.emr_no_vcpus[local.environment]
      core_instance_type_1 = var.emr_core_instance_type_1[local.environment]
      core_instance_type_2 = var.emr_core_instance_type_2[local.environment]
      weightedcapacity_1   = var.emr_weightedcapacity_1[local.environment]
      weightedcapacity_2   = var.emr_weightedcapacity_2[local.environment]
    }
  )
}

resource "aws_s3_bucket_object" "steps" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/steps.yaml"
  content = templatefile("${path.module}/cluster_config/steps.yaml.tpl",
    {
      s3_config_bucket = data.terraform_remote_state.common.outputs.config_bucket.id
    }
  )
}

resource "aws_s3_bucket_object" "configurations" {
  bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  key    = "emr/adg/configurations.yaml"
  content = templatefile("${path.module}/cluster_config/configurations.yaml.tpl",
    {
      s3_log_bucket            = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
      s3_log_prefix            = local.s3_log_prefix
      s3_published_bucket      = aws_s3_bucket.published.id
      s3_ingest_bucket         = data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket
      hbase_root_path          = local.hbase_root_path
      proxy_no_proxy           = replace(replace(local.no_proxy, ",", "|"), ".s3", "*.s3")
      proxy_http_host          = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_http_port          = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      proxy_https_host         = data.terraform_remote_state.internal_compute.outputs.internet_proxy.host
      proxy_https_port         = data.terraform_remote_state.internal_compute.outputs.internet_proxy.port
      emrfs_metadata_tablename = local.emrfs_metadata_tablename
      maxExecutors             = var.emr_maxExecutors[local.environment]
      minExecutors             = var.emr_minExecutors[local.environment]
      s3_htme_bucket           = data.terraform_remote_state.ingest.outputs.s3_buckets.htme_bucket
    }
  )
}
