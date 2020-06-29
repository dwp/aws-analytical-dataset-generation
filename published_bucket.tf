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

data "aws_iam_policy_document" "published_bucket_kms_key" {
  statement {
    sid       = "Enable root-delegated access control"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account[local.environment]}:root"]
    }
  }
}

resource "aws_kms_key" "published_bucket_cmk" {
  description             = "UCFS published Bucket Master Key"
  deletion_window_in_days = 7
  is_enabled              = true
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.published_bucket_kms_key.json

  # ProtectsSensitiveData = "False" because, although this bucket is likely to
  # contain PII, its primary form of protection should be CloudHSM-managed
  # key material, meaning a default KMS key policy can be used
  tags = merge(
    local.tags,
    {
      Name = "published_bucket_cmk"
    },
    {
      ProtectsSensitiveData = "False"
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
  tags = merge(
    local.tags,
    {
      Name = "published_bucket"
  })

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
  bucket     = aws_s3_bucket.published.id
  policy     = data.aws_iam_policy_document.published_bucket_https_only.json
  depends_on = [aws_s3_bucket_public_access_block.published]
}

data "aws_iam_policy_document" "analytical_dataset_generator_write_parquet" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.published.arn,
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
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_write_parquet" {
  name        = "AnalyticalDatasetGeneratorWriteParquet"
  description = "Allow writing of Analytical Dataset parquet files"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_write_parquet.json
}
