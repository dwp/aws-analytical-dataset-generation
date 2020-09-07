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
  type                     = "ingress"
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

resource "random_id" "password_salt" {
  byte_length = 16
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
  master_username         = var.metadata_store_master_username
  master_password         = "password_already_rotated_${substr(random_id.password_salt.hex, 0, 16)}"
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

output "writer_endpoint" {
  value = "${aws_rds_cluster.hive_metastore.endpoint}"
}

resource "aws_secretsmanager_secret" "metadata_store_master" {
  name        = "metadata-store-${var.metadata_store_master_username}"
  description = "Metadata Store master password"
}

# Create entries for additional SQL users
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
    sg_id = aws_security_group.hive_metastore.id
  }
}

