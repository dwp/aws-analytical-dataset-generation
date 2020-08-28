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

// TODO: Lock this down to ADG, PDM & analytical-env after the spike
resource "aws_security_group_rule" "allow_all_hive_metastore_ingress" {
  security_group_id = aws_security_group.hive_metastore.id
  type              = "ingress"
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  to_port           = 3306
  protocol          = "tcp"
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

// TODO: Convert username/password to secrets after the spike
resource "aws_rds_cluster" "hive_metastore" {
  cluster_identifier      = "hive-metastore"
  engine                  = "aurora-mysql"
  engine_version          = "5.7.mysql_aurora.2.08.1"
  engine_mode             = "provisioned"
  availability_zones      = data.aws_availability_zones.available.names
  db_subnet_group_name    = aws_db_subnet_group.internal_compute.name
  database_name           = "hive_metastore"
  master_username         = "hive"
  master_password         = "hivepassword"
  backup_retention_period = 7
  vpc_security_group_ids  = [aws_security_group.hive_metastore.id]
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.hive_metastore.arn
  tags                    = merge(local.common_tags, { Name = "hive-metastore" })
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count                = local.hive_metastore_instance_count[local.environment]
  identifier           = "hive-metastore-${count.index}"
  cluster_identifier   = aws_rds_cluster.hive_metastore.id
  instance_class       = local.hive_metastore_instance_type[local.environment]
  db_subnet_group_name = aws_rds_cluster.hive_metastore.db_subnet_group_name
  engine               = aws_rds_cluster.hive_metastore.engine
  engine_version       = aws_rds_cluster.hive_metastore.engine_version
  tags                 = merge(local.common_tags, { Name = "hive-metastore" })
}
