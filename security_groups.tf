resource "aws_security_group" "adg_master" {
  name                   = "ADG Master"
  description            = "Contains rules for ADG master nodes; most rules are injected by EMR, not managed by TF"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "adg_slave" {
  name                   = "ADG Slave"
  description            = "Contains rules for ADG slave nodes; most rules are injected by EMR, not managed by TF"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "adg_common" {
  name                   = "ADG Common"
  description            = "Contains rules for both ADG master and ADG slave nodes"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group" "adg_emr_service" {
  name                   = "ADG EMR Service"
  description            = "Contains rules for EMR service when managing the ADG cluster; rules are injected by EMR, not managed by TF"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

resource "aws_security_group_rule" "egress_https_to_vpc_endpoints" {
  description              = "Allow HTTPS traffic to VPC endpoints"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.adg_common.id
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
  source_security_group_id = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_https_s3_endpoint" {
  description       = "Allow HTTPS access to S3 via its endpoint"
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  prefix_list_ids   = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.s3_prefix_list_id]
  security_group_id = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_http_s3_endpoint" {
  description       = "Allow HTTP access to S3 via its endpoint (YUM)"
  type              = "egress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  prefix_list_ids   = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.s3_prefix_list_id]
  security_group_id = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_internet_proxy" {
  description       = "Allow Internet access via the proxy (for ACM-PCA)"
  type              = "egress"
  from_port         = 3128
  to_port           = 3128
  protocol          = "tcp"
  cidr_blocks       = data.terraform_remote_state.internet_egress.outputs.proxy_subnet.cidr_blocks
  security_group_id = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_hbase_zookeeper" {
  description              = "Allow Ingest-HBase Zookeeper requests"
  type                     = "egress"
  from_port                = 2181
  to_port                  = 2181
  protocol                 = "tcp"
  source_security_group_id = data.terraform_remote_state.ingest.outputs.emr_common_sg.id
  security_group_id        = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_hbase_master" {
  description              = "Allow Ingest-HBase Master requests"
  type                     = "egress"
  from_port                = 16000
  to_port                  = 16000
  protocol                 = "tcp"
  source_security_group_id = data.terraform_remote_state.ingest.outputs.emr_common_sg.id
  security_group_id        = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_hbase_regionserver" {
  description              = "Allow Ingest-HBase RegionServer traffic"
  type                     = "egress"
  from_port                = 16020
  to_port                  = 16020
  protocol                 = "tcp"
  source_security_group_id = data.terraform_remote_state.ingest.outputs.emr_common_sg.id
  security_group_id        = aws_security_group.adg_common.id
}

# The EMR service will automatically add the ingress equivalent of this rule,
# but doesn't inject this egress counterpart
resource "aws_security_group_rule" "emr_master_to_core_egress" {
  description              = "Allow master nodes to send traffic to core nodes"
  type                     = "egress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.adg_slave.id
  security_group_id        = aws_security_group.adg_master.id
}

# The EMR service will automatically add the ingress equivalent of this rule,
# but doesn't inject this egress counterpart
resource "aws_security_group_rule" "emr_core_to_master_egress" {
  description              = "Allow core nodes to send traffic to master nodes"
  type                     = "egress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.adg_master.id
  security_group_id        = aws_security_group.adg_slave.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Ganglia"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_80" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Ganglia"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_master.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Hbase"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_hbase" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Hbase"
  type              = "ingress"
  from_port         = 16010
  to_port           = 16010
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_master.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Spark"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_spark" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Spark"
  type              = "ingress"
  from_port         = 18080
  to_port           = 18080
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_master.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Yarn NodeManager"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_yarn_nm" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Yarn NodeManager"
  type              = "ingress"
  from_port         = 8042
  to_port           = 8042
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_master.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Yarn ResourceManager"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_yarn_rm" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Yarn ResourceManager"
  type              = "ingress"
  from_port         = 8088
  to_port           = 8088
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_master.id
}

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Region Server"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_slave_region_server" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Region Server"
  type              = "ingress"
  from_port         = 16030
  to_port           = 16030
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.adg_slave.id
}
