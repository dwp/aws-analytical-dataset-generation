data "template_file" "cluster" {
  template = file("cluster_config/cluster.yaml.tpl")

  vars = {
    s3_log_bucket    = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
    ami_id           = var.emr_ami_id
    service_role     = aws_iam_role.analytical_dataset_generator.arn
    instance_profile = aws_iam_instance_profile.analytical_dataset_generator.arn
  }
}

resource "aws_s3_bucket_object" "cluster" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/cluster.yaml"
  content    = data.template_file.cluster.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "instances" {
  template = file("cluster_config/instances.yaml.tpl")

  vars = {
    add_master_sg     = aws_security_group.analytical_dataset_generation.id
    add_slave_sg      = aws_security_group.analytical_dataset_generation.id
    subnet_id         = data.terraform_remote_state.internal_compute.outputs.htme_subnet.ids[0]
    master_sg         = aws_security_group.master_sg.id
    slave_sg          = aws_security_group.slave_sg.id
    service_access_sg = aws_security_group.service_access_sg.id
    instance_type     = var.emr_instance_type[local.environment]
  }
}

resource "aws_s3_bucket_object" "instances" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/instances.yaml"
  content    = data.template_file.instances.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "steps" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/steps.yaml"
  content    = data.template_file.steps.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

data "template_file" "steps" {
  template = file("cluster_config/steps.yaml.tpl")

  vars = {
    s3_config_bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  }
}

data "template_file" "configurations" {
  template = file("cluster_config/configurations.yaml.tpl")

  vars = {
    s3_log_bucket       = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
    s3_published_bucket = aws_s3_bucket.published.id
    s3_ingest_bucket    = data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket
    hbase_root_path     = local.hbase_root_path
    proxy_no_proxy      = "169.254.169.254|*.s3.eu-west-2.amazonaws.com|s3.eu-west-2.amazonaws.com|sns.eu-west-2.amazonaws.com|sqs.eu-west-2.amazonaws.com|eu-west-2.queue.amazonaws.com|glue.eu-west-2.amazonaws.com|sts.eu-west-2.amazonaws.com|*.eu-west-2.compute.internal|dynamodb.eu-west-2.amazonaws.com"
    proxy_http_address  = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.http_address
    proxy_https_address = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.https_address
  }
}

resource "aws_s3_bucket_object" "configurations" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/configurations.yaml"
  content    = data.template_file.configurations.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}
