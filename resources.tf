data "aws_iam_user" "breakglass" {
  user_name = "breakglass"
}

data "aws_iam_role" "ci" {
  name = "ci"
}

data "aws_iam_role" "administrator" {
  name = "administrator"
}

data "aws_iam_role" "aws_config" {
  name = "aws_config"
}

#Create policy document
data "aws_iam_policy_document" "published_bucket_kms_key" {

  statement {
    sid    = "EnableIAMPermissionsBreakglass"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_user.breakglass.arn]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid       = "EnableIAMPermissionsCI"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      identifiers = [data.aws_iam_role.ci.arn]
      type        = "AWS"
    }
  }

  statement {
    sid    = "DenyCIEncryptDecrypt"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_role.ci.arn]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ImportKeyMaterial",
      "kms:ReEncryptFrom",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "EnableIAMPermissionsAdministrator"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_role.administrator.arn]
    }

    actions = [
      "kms:Describe*",
      "kms:List*",
      "kms:Get*"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "EnableAWSConfigManagerScanForSecurityHub"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_role.aws_config.arn]
    }

    actions = [
      "kms:Describe*",
      "kms:Get*",
      "kms:List*"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "EnableIAMPermissionsAnalyticDatasetGen"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.analytical_dataset_generator.arn]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]

    resources = ["*"]

  }

}

resource "aws_kms_key" "published_bucket_cmk" {
  description             = "UCFS published Bucket Master Key"
  deletion_window_in_days = 7
  is_enabled              = true
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.published_bucket_kms_key.json


  tags = merge(
    local.tags,
    {
      Name = "published_bucket_cmk"
    },
    {
      requires-custom-key-policy = "True"
    }
  )
}

resource "aws_kms_alias" "published_bucket_cmk" {
  name          = "alias/published_bucket_cmk"
  target_key_id = aws_kms_key.published_bucket_cmk.key_id
}

output "published_bucket_cmk" {
  value = {
    arn = aws_kms_key.published_bucket_cmk.arn
  }
}

resource "random_id" "published_bucket" {
  byte_length = 16
}

resource "aws_s3_bucket" "published" {
  tags   = local.tags
  bucket = random_id.published_bucket.hex
  acl    = "private"

  versioning {
    enabled = true
  }

  logging {
    target_bucket = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
    target_prefix = "S3Logs/${random_id.published_bucket.hex}/ServerLogs"
  }

  lifecycle_rule {
    id      = ""
    prefix  = "/"
    enabled = true

    noncurrent_version_expiration {
      days = 30
    }
  }

  # TODO add back logging. DW-3608

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.published_bucket_cmk.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "published" {
  bucket = aws_s3_bucket.published.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

output "published_bucket" {
  value = {
    id  = aws_s3_bucket.published.id
    arn = aws_s3_bucket.published.arn
  }
}

data "aws_iam_policy_document" "published_bucket_https_only" {
  statement {
    sid     = "BlockHTTP"
    effect  = "Deny"
    actions = ["*"]

    resources = [
      aws_s3_bucket.published.arn,
      "${aws_s3_bucket.published.arn}/*",
    ]

    principals {
      identifiers = ["*"]
      type        = "AWS"
    }

    condition {
      test     = "Bool"
      values   = ["false"]
      variable = "aws:SecureTransport"
    }
  }
}

resource "aws_s3_bucket_policy" "published_bucket_https_only" {
  bucket = aws_s3_bucket.published.id
  policy = data.aws_iam_policy_document.published_bucket_https_only.json
}

resource "aws_iam_role" "analytical_dataset_generator" {
  name               = "analytical_dataset_generator"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.tags
}

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

data "aws_iam_policy_document" "analytical_dataset_acm" {
  statement {
    effect = "Allow"

    actions = [
      "acm:ExportCertificate",
    ]

    resources = [
      aws_acm_certificate.analytical-dataset-generator.arn
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_acm" {
  name        = "DatasetGeneratorACM"
  description = "Allow Dataset Generator clusters to export acm"
  policy      = data.aws_iam_policy_document.analytical_dataset_acm.json
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_acm" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_acm.arn
}

resource "aws_secretsmanager_secret" "adg_secret" {
  name = "ADG-Payload"
}

data "aws_iam_policy_document" "analytical_dataset_secretsmanager" {
  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      aws_secretsmanager_secret.adg_secret.arn
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
  name                   = "analytical_dataset_generation_common"
  description            = "Contains rules for both EMR cluster master nodes and EMR cluster slave nodes"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.vpc.vpc.id
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


resource "aws_acm_certificate" "analytical-dataset-generator" {
  certificate_authority_arn = data.terraform_remote_state.aws_certificate_authority.outputs.root_ca.arn
  domain_name               = "analytical-dataset-generator.${local.env_prefix[local.environment]}${local.dataworks_domain_name}"

  options {
    certificate_transparency_logging_preference = "DISABLED"
  }
}

