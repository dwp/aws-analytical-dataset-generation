resource "aws_security_group" "master_sg" {
  name                   = "analytical_dataset_generation_master_sg"
  description            = "Contains rules for EMR master"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "slave_sg" {
  name                   = "analytical_dataset_generation_slave_sg"
  description            = "Contains rules for EMR slave"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "service_access_sg" {
  name                   = "analytical_dataset_generation_service_access_sg"
  description            = "Contains rules for EMR cluster"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "common_sg" {
  name                   = "analytical_dataset_generation_additional_common"
  description            = "Contains rules common to both master and slave nodes"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group_rule" "egress_https_to_vpc_endpoints" {
  description              = "Allow HTTPS traffic to VPC endpoints"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.common_sg.id
  to_port                  = 443
  type                     = "egress"
  source_security_group_id = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.interface_vpce_sg_id
}

resource "aws_security_group_rule" "ingress_https_vpc_endpoints_from_emr" {
  description              = "Allow HTTPS traffic from Analytical Dataset Generator"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.interface_vpce_sg_id
  to_port                  = 443
  type                     = "ingress"
  source_security_group_id = aws_security_group.common_sg.id
}

resource "aws_security_group_rule" "egress_https_s3_endpoint" {
  description       = "Allow HTTPS access to S3 via its endpoint"
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  prefix_list_ids   = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.s3_prefix_list_id]
  security_group_id = aws_security_group.common_sg.id
}

resource "aws_security_group_rule" "egress_https_s3_endpoint" {
  description       = "Allow Internet access via the proxy (for ACM-PCA)"
  type              = "ingress"
  from_port         = 3128
  to_port           = 3128
  protocol          = "tcp"
  cidr_blocks       = data.terraform_remote_state.internet_egress.outputs.proxy_subnet.cidr_blocks
  security_group_id = aws_security_group.common_sg.id
}
