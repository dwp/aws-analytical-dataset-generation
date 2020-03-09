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
