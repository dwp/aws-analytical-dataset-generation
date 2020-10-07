resource "aws_db_subnet_group" "internal_compute" {
  name       = "hive-metastore"
  subnet_ids = data.terraform_remote_state.internal_compute.outputs.pdm_subnet.ids

  tags = merge(local.common_tags, { Name = "hive-metastore" })
}

resource "aws_security_group" "hive_metastore" {
  name        = "hive_metastore"
  description = "Controls access to the Hive Metastore"
  vpc_id      = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
  tags        = merge(local.common_tags, { Name = "hive-metastore" })
}

resource "aws_security_group_rule" "ingress_adg" {
  description              = "Allow mysql traffic to Aurora RDS from ADG"
  from_port                = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.hive_metastore.id
  to_port                  = 3306
  type                     = "ingress"
  source_security_group_id = aws_security_group.adg_common.id
}

resource "aws_security_group_rule" "egress_adg" {
  description              = "Allow mysql traffic to Aurora RDS from ADG"
  from_port                = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.adg_common.id
  to_port                  = 3306
  type                     = "egress"
  source_security_group_id = aws_security_group.hive_metastore.id
}

resource "aws_kms_key" "hive_metastore" {
  description             = "Protects the Hive Metastore database"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags = merge(
    local.common_tags,
    {
      Name                  = "hive-metastore"
      ProtectsSensitiveData = "false"
    },
  )
}

resource "aws_kms_alias" "hive_metastore" {
  name          = "alias/hive-metastore"
  target_key_id = aws_kms_key.hive_metastore.id
}

resource "aws_kms_key" "hive_metastore_perf_insights" {
  description             = "Protects Hive Metastore's Performance Insights"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags = merge(
    local.common_tags,
    {
      Name                  = "hive-metastore-perf-insights"
      ProtectsSensitiveData = "false"
    },
  )
}

resource "aws_kms_alias" "hive_metastore_perf_insights" {
  name          = "alias/hive-metastore-perf-insights"
  target_key_id = aws_kms_key.hive_metastore_perf_insights.id
}

resource "aws_kms_key" "hive_metastore_logs" {
  description             = "Protects Hive Metastore's CloudWatch Logs"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags = merge(
    local.common_tags,
    {
      Name                  = "hive-metastore-logs"
      ProtectsSensitiveData = "false"
    },
  )
}

resource "aws_kms_alias" "hive_metastore_logs" {
  name          = "alias/hive-metastore-logs"
  target_key_id = aws_kms_key.hive_metastore_logs.id
}

resource "aws_cloudwatch_log_group" "hive_metastore_audit" {
  name              = "/aws/rds/instance/hive-metastore/audit"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.hive_metastore_logs.arn
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "hive_metastore_general" {
  name              = "/aws/rds/instance/hive-metastore/general"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.hive_metastore_logs.arn
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "hive_metastore_slowquery" {
  name              = "/aws/rds/instance/hive-metastore/slowquery"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.hive_metastore_logs.arn
  tags              = local.common_tags
}

resource "aws_rds_cluster_parameter_group" "hive_metastore_logs" {
  name        = "hive-metastore-logs"
  family      = "aurora-mysql-5.7"
  description = "Logging parameters for Hive Metastore"

  parameter {
    name  = "log_output"
    value = "FILE"
  }

  parameter {
    name  = "general_log"
    value = "1"
  }

  parameter {
    name  = "slow_query_log"
    value = "1"
  }
}

data "aws_iam_policy_document" "rds_em_assume_role" {
  statement {
    sid     = "RDSEMAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["monitoring.rds.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  name               = "rds_enhanced_monitoring"
  assume_role_policy = data.aws_iam_policy_document.rds_em_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "random_id" "password_salt" {
  byte_length = 16
}

resource "aws_rds_cluster" "hive_metastore" {
  cluster_identifier              = "hive-metastore"
  engine                          = "aurora-mysql"
  engine_version                  = local.emr_engine_version[local.environment]
  engine_mode                     = "provisioned"
  availability_zones              = data.aws_availability_zones.available.names
  db_subnet_group_name            = aws_db_subnet_group.internal_compute.name
  database_name                   = "hive_metastore"
  master_username                 = var.metadata_store_master_username
  master_password                 = "password_already_rotated_${substr(random_id.password_salt.hex, 0, 16)}"
  backup_retention_period         = 7
  vpc_security_group_ids          = [aws_security_group.hive_metastore.id]
  storage_encrypted               = true
  kms_key_id                      = aws_kms_key.hive_metastore.arn
  enabled_cloudwatch_logs_exports = ["audit", "general", "slowquery"]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.hive_metastore_logs.name
  apply_immediately               = true
  tags                            = merge(local.common_tags, { Name = "hive-metastore" })

  lifecycle {
    ignore_changes = [master_password]
  }
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count                           = local.hive_metastore_instance_count[local.environment]
  identifier                      = "hive-metastore-${count.index}"
  cluster_identifier              = aws_rds_cluster.hive_metastore.id
  instance_class                  = local.hive_metastore_instance_type[local.environment]
  db_subnet_group_name            = aws_rds_cluster.hive_metastore.db_subnet_group_name
  tags                            = merge(local.common_tags, { Name = "hive-metastore" })
  engine                          = aws_rds_cluster.hive_metastore.engine
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.hive_metastore_perf_insights.arn
  monitoring_interval             = local.hive_metastore_monitoring_interval[local.environment]
  monitoring_role_arn             = aws_iam_role.rds_enhanced_monitoring.arn
  apply_immediately               = true
}

resource "aws_secretsmanager_secret" "metadata_store_master" {
  name        = "metadata-store-${var.metadata_store_master_username}"
  description = "Metadata Store master password"
  tags        = local.common_tags
  policy      = data.aws_iam_policy_document.admin_access_to_metadata_secrets.json
}

resource "aws_secretsmanager_secret_version" "metadata_store_master" {
  secret_id = aws_secretsmanager_secret.metadata_store_master.id
  secret_string = jsonencode({
    "username" = "${var.metadata_store_master_username}",
    "password" = "${aws_rds_cluster.hive_metastore.master_password}",
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Create entries for additional SQL users
data "aws_iam_policy_document" "admin_access_to_metadata_secrets" {
  statement {
    sid       = "DelegateToIAM"
    effect    = "Allow"
    resources = ["*"]
    actions   = ["secretsmanager:*"]
    principals {
      identifiers = ["arn:aws:iam::${local.account[local.environment]}:root"]
      type        = "AWS"
    }
  }

  statement {
    sid       = "GrantAdminsSecretValueAccess"
    effect    = "Allow"
    resources = ["*"]
    actions   = ["secretsmanager:GetSecretValue"]
    principals {
      identifiers = ["arn:aws:iam::${local.account[local.environment]}:role/administrator"]
      type        = "AWS"
    }
  }
}

resource "aws_secretsmanager_secret" "metadata_store_adg_reader" {
  name        = "metadata-store-${var.metadata_store_adg_reader_username}"
  description = "${var.metadata_store_adg_reader_username} SQL user for Metadata Store"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "metadata_store_adg_writer" {
  name        = "metadata-store-${var.metadata_store_adg_writer_username}"
  description = "${var.metadata_store_adg_writer_username} SQL user for Metadata Store"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "metadata_store_pdm_writer" {
  name        = "metadata-store-${var.metadata_store_pdm_writer_username}"
  description = "${var.metadata_store_pdm_writer_username} SQL user for Metadata Store"
  tags        = local.common_tags
}

output "hive_metastore" {
  value = {
    security_group = aws_security_group.hive_metastore
    rds_cluster    = aws_rds_cluster.hive_metastore
    database_name  = aws_rds_cluster.hive_metastore.database_name
  }
}
