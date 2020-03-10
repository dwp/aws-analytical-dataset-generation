# KMS Key Creation

resource "aws_kms_key" "published_bucket_cmk" {
  description             = "UCFS published Bucket Master Key"
  deletion_window_in_days = 7
  is_enabled              = true
  enable_key_rotation     = true

  tags = merge(
    local.tags,
    {
      Name = "published_bucket_cmk"
    },
    {
      #TODO add custom key policy if required DW-3607
      requires-custom-key-policy = "False"
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

# S3 Bucket creation

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

# IAM Role and Instance Profile creation

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
      identifiers = ["ec2.amazonaws.com"]
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
#        TODO Lock down analytical dataset EMR instance profile DW-3618
data "aws_iam_policy_document" "analytical_dataset_write_s3" {
  statement {
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      "arn:aws:s3:::*",
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
      "arn:aws:s3:::*",
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
      "arn:aws:kms:::*",
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
  }
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

# Security groups

resource "aws_security_group" "analytical_dataset_generation" {
  name                   = "analytical_dataset_generation_common"
  description            = "Contains rules for both EMR cluster master nodes and EMR cluster slave nodes"
  revoke_rules_on_delete = true
  #vpc_id                 = module.vpc.vpc_id
}

resource "aws_security_group_rule" "analytical_dataset_generation_egress" {
  description       = "Allow outbound traffic from Analytical Dataset Generation EMR Cluster"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  #prefix_list_ids   = [module.vpc.s3_prefix_list_id]
  security_group_id = aws_security_group.analytical_dataset_generation.id
}

resource "aws_security_group_rule" "analytical_dataset_generation_ingress" {
  description       = "Allow inbound traffic from Analytical Dataset Generation EMR Cluster"
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  #prefix_list_ids   = [module.vpc.s3_prefix_list_id]
  security_group_id = aws_security_group.analytical_dataset_generation.id
}

resource "aws_security_group" "analytical_dataset_generation_service" {
  name                   = "analytical_dataset_generation_service"
  description            = "Contains rules automatically added by the EMR service itself. See https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-man-sec-groups.html#emr-sg-elasticmapreduce-sa-private"
  revoke_rules_on_delete = true
  #vpc_id                 = module.vpc.vpc_id
}

#TODO add logging bucket

output "analytical_dataset_generation_sg" {
  value = {
    id = aws_security_group.analytical_dataset_generation.id
  }
}
