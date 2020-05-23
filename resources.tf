resource "aws_iam_instance_profile" "analytical_dataset_generator" {
  name = "analytical_dataset_generator"
  role = aws_iam_role.analytical_dataset_generator.id
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com", "elasticmapreduce.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

#        Attach AWS policies
resource "aws_iam_role_policy_attachment" "emr_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"

}

resource "aws_iam_role_policy_attachment" "emr_for_ec2_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"

}

resource "aws_iam_role_policy_attachment" "ec2_for_ssm_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"

}

#        Create and attach custom policy
data "aws_iam_policy_document" "analytical_dataset_gluetables" {
  statement {
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
    ]

    resources = [
      "arn:aws:glue:::database/aws_glue_catalog_database.analytical_dataset_generation_staging.name",
      "arn:aws:glue:::database/aws_glue_catalog_database.analytical_dataset_generation.name",
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_gluetables" {
  name        = "DatasetGeneratorGlueTables"
  description = "Allow Dataset Generator clusters to create drop tables"
  policy      = data.aws_iam_policy_document.analytical_dataset_gluetables.json
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_gluetables" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_gluetables.arn
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_acm" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_acm.arn
}

# Create and attach custom policy to allow use of CMK for EBS encryption
data "aws_iam_policy_document" "analytical_dataset_ebs_cmk" {
  statement {
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]

    resources = [data.terraform_remote_state.security-tools.outputs.ebs_cmk.arn]
  }

  statement {
    effect = "Allow"

    actions = ["kms:CreateGrant"]

    resources = [data.terraform_remote_state.security-tools.outputs.ebs_cmk.arn]

    condition {
      test     = "Bool"
      variable = "kms:GrantIsForAWSResource"
      values   = ["true"]
    }
  }
}

resource "aws_iam_policy" "analytical_dataset_ebs_cmk" {
  name        = "DataGenerationEmrUseEbsCmk"
  description = "Allow Analytical EMR cluster to use EB CMK for encryption"
  policy      = data.aws_iam_policy_document.analytical_dataset_ebs_cmk.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_ebs_cmk" {
  role       = aws_iam_role.analytical_dataset_generator.id
  policy_arn = aws_iam_policy.analytical_dataset_ebs_cmk.arn
}

data "aws_iam_policy_document" "analytical_dataset_write_s3" {

  statement {
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.published.arn,
      "${data.terraform_remote_state.common.outputs.config_bucket.arn}",
      "arn:aws:s3:::${data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket}",
      "arn:aws:s3:::${data.terraform_remote_state.security-tools.outputs.logstore_bucket.id}",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
      "s3:DeleteObject*",
      "s3:PutObject*",
    ]

    resources = [
      "${aws_s3_bucket.published.arn}/*",
      "arn:aws:s3:::${data.terraform_remote_state.ingest.outputs.s3_buckets.hbase_rootdir}/data/hbase/meta_*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
      "s3:PutObject*",
    ]

    resources = [
      "arn:aws:s3:::${data.terraform_remote_state.security-tools.outputs.logstore_bucket.id}",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.config_bucket.arn}/component/analytical-dataset-generation/*",
      "arn:aws:s3:::${data.terraform_remote_state.ingest.outputs.s3_buckets.hbase_rootdir}/*",
    ]
  }


  statement {
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]

    resources = [
      "${aws_kms_key.published_bucket_cmk.arn}",
      "${data.terraform_remote_state.ingest.outputs.input_bucket_cmk.arn}",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.config_bucket_cmk.arn}",
      "${data.terraform_remote_state.ingest.outputs.input_bucket_cmk.arn}",
    ]
  }

  statement {
    sid    = "AllowUseDefaultEbsCmk"
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]
    resources = [data.terraform_remote_state.security-tools.outputs.ebs_cmk.arn]
  }

  statement {
    sid       = "AllowAccessToArtefactBucket"
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation"]
    resources = [data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn]
  }

  statement {
    sid       = "AllowPullFromArtefactBucket"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn}/*"]
  }

  statement {
    sid    = "AllowDecryptArtefactBucket"
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [data.terraform_remote_state.management_artefact.outputs.artefact_bucket.cmk_arn]
  }
}

resource "aws_iam_role_policy_attachment" "amazon_ssm_managed_instance_core" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.analytical_dataset_generator.name
}

resource "aws_iam_policy" "analytical_dataset_write_s3" {
  name        = "DatasetGeneratorWriteS3"
  description = "Allow Dataset Generator clusters to write to S3 buckets"
  policy      = data.aws_iam_policy_document.analytical_dataset_write_s3.json
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_write_s3" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_write_s3.arn
}

resource "aws_security_group" "analytical_dataset_generation" {
  name                   = "analytical_dataset_generation_additional_common"
  description            = "Contains rules for both EMR cluster master nodes and EMR cluster slave nodes"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
}

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

# DW-4134 - Rule for the dev Workspaces, gated to dev - "Ganglia"
resource "aws_security_group_rule" "emr_server_ingress_workspaces_master_80" {
  count             = local.environment == "development" ? 1 : 0
  description       = "Allow WorkSpaces (internal-compute VPC) access to Ganglia"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.cidr_block]
  security_group_id = aws_security_group.master_sg.id
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
  security_group_id = aws_security_group.master_sg.id
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
  security_group_id = aws_security_group.master_sg.id
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
  security_group_id = aws_security_group.master_sg.id
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
  security_group_id = aws_security_group.master_sg.id
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
  security_group_id = aws_security_group.slave_sg.id
}

resource "aws_security_group_rule" "ingress_tcp_master_master" {
  description              = "ingress_tcp_master_master"
  from_port                = 0
  protocol                 = "tcp"
  security_group_id        = aws_security_group.master_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.master_sg.id
}

resource "aws_security_group_rule" "ingress_tcp_slave_master" {
  description              = "ingress_tcp_slave_master"
  from_port                = 0
  protocol                 = "tcp"
  security_group_id        = aws_security_group.master_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.slave_sg.id
}

resource "aws_security_group_rule" "ingress_tcp_service_master" {
  description              = "ingress_tcp_service_master"
  from_port                = 8443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.master_sg.id
  to_port                  = 8443
  type                     = "ingress"
  source_security_group_id = aws_security_group.service_access_sg.id
}

resource "aws_security_group_rule" "ingress_udp_master_master" {
  description              = "ingress_udp_master_master"
  from_port                = 0
  protocol                 = "udp"
  security_group_id        = aws_security_group.master_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.master_sg.id
}

resource "aws_security_group_rule" "ingress_udp_slave_master" {
  description              = "ingress_udp_slave_master"
  from_port                = 0
  protocol                 = "udp"
  security_group_id        = aws_security_group.master_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.slave_sg.id
}

resource "aws_security_group_rule" "egress_all_traffic_master" {
  description       = "egress_all_traffic_master"
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.master_sg.id
  to_port           = 0
  type              = "egress"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "ingress_tcp_master_slave" {
  description              = "ingress_tcp_master_slave"
  from_port                = 0
  protocol                 = "tcp"
  security_group_id        = aws_security_group.slave_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.master_sg.id
}

resource "aws_security_group_rule" "ingress_tcp_slave_slave" {
  description              = "ingress_tcp_slave_slave"
  from_port                = 0
  protocol                 = "tcp"
  security_group_id        = aws_security_group.slave_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.slave_sg.id
}

resource "aws_security_group_rule" "ingress_tcp_service_slave" {
  description              = "ingress_tcp_service_slave"
  from_port                = 8443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.slave_sg.id
  to_port                  = 8443
  type                     = "ingress"
  source_security_group_id = aws_security_group.service_access_sg.id
}

resource "aws_security_group_rule" "ingress_udp_master_slave" {
  description              = "ingress_udp_master_slaver"
  from_port                = 0
  protocol                 = "udp"
  security_group_id        = aws_security_group.slave_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.master_sg.id
}

resource "aws_security_group_rule" "ingress_udp_slave_slave" {
  description              = "ingress_udp_slave_slave"
  from_port                = 0
  protocol                 = "udp"
  security_group_id        = aws_security_group.slave_sg.id
  to_port                  = 65535
  type                     = "ingress"
  source_security_group_id = aws_security_group.slave_sg.id
}

resource "aws_security_group_rule" "egress_all_traffic_slave" {
  description       = "egress_all_traffic_slave"
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.slave_sg.id
  to_port           = 0
  type              = "egress"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "egress_https_to_vpc_endpoints" {
  description              = "egress_https_to_vpc_endpoints"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.analytical_dataset_generation.id
  to_port                  = 443
  type                     = "egress"
  source_security_group_id = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.interface_vpce_sg_id
}

resource "aws_security_group_rule" "ingress_https_vpc_endpoints_from_emr" {
  description              = "ingress_https_vpc_endpoints_from_emr"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.interface_vpce_sg_id
  to_port                  = 443
  type                     = "ingress"
  source_security_group_id = aws_security_group.analytical_dataset_generation.id
}

#TODO add logging bucket

output "analytical_dataset_generation_sg" {
  value = aws_security_group.analytical_dataset_generation
}

# Glue Database creation

resource "aws_glue_catalog_database" "analytical_dataset_generation" {
  name        = "analytical_dataset_generation"
  description = "Database for the Manifest comparision ETL"
}

output "analytical_dataset_generation" {
  value = {
    job_name = aws_glue_catalog_database.analytical_dataset_generation.name
  }
}

resource "aws_glue_catalog_database" "analytical_dataset_generation_staging" {
  name        = "analytical_dataset_generation_staging"
  description = "Staging Database for analytical dataset generation"
}

output "analytical_dataset_generation_staging" {
  value = {
    job_name = aws_glue_catalog_database.analytical_dataset_generation_staging.name
  }
}

data "aws_secretsmanager_secret" "adg_secret" {
  name = local.secret_name
}

data "aws_iam_policy_document" "analytical_dataset_secretsmanager" {
  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      data.aws_secretsmanager_secret.adg_secret.arn
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_secretsmanager" {
  name        = "DatasetGeneratorSecretsManager"
  description = "Allow Dataset Generator clusters to get secrets"
  policy      = data.aws_iam_policy_document.analytical_dataset_secretsmanager.json
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_secretsmanager" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_secretsmanager.arn
}


