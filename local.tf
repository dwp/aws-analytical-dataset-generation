locals {
  emr_cluster_name                = "aws-analytical-dataset-generator"
  master_instance_type            = "m5.2xlarge"
  core_instance_type              = "m5.2xlarge"
  core_instance_count             = 1
  task_instance_type              = "m5.2xlarge"
  ebs_root_volume_size            = 100
  ebs_config_size                 = 250
  ebs_config_type                 = "gp2"
  ebs_config_volumes_per_instance = 1
  autoscaling_min_capacity        = 0
  autoscaling_max_capacity        = 5
  dks_port                        = 8443
  common_tags = {
    Environment  = local.environment
    Application  = local.emr_cluster_name
    CreatedBy    = "terraform"
    Owner        = "dataworks platform"
    Persistence  = "Ignore"
    AutoShutdown = "False"
  }
  internet_proxy = data.terraform_remote_state.internet_egress.outputs.internet_proxy
}


