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

    resources = [
      "arn:aws:kms:::*",
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

resource "aws_security_group" "analytical_dataset_generation" {
  name                   = "analytical_dataset_generation_common"
  description            = "Contains rules for both EMR cluster master nodes and EMR cluster slave nodes"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.id 
}

resource "aws_security_group_rule" "analytical_dataset_generation_egress" {
  description       = "Allow outbound traffic from Analytical Dataset Generation EMR Cluster"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  #prefix_list_ids   = [module.vpc.s3_prefix_list_id]
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.analytical_dataset_generation.id
}

resource "aws_security_group_rule" "analytical_dataset_generation_ingress" {
  description       = "Allow inbound traffic from Analytical Dataset Generation EMR Cluster"
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  #prefix_list_ids   = [module.vpc.s3_prefix_list_id]
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.analytical_dataset_generation.id
}

resource "aws_security_group" "analytical_dataset_generation_service" {
  name                   = "analytical_dataset_generation_service"
  description            = "Contains rules automatically added by the EMR service itself. See https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-man-sec-groups.html#emr-sg-elasticmapreduce-sa-private"
  revoke_rules_on_delete = true
  vpc_id                 = data.terraform_remote_state.internal_compute.outputs.vpc.id 
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

# Some of these permissions may not be required, this is a copy of the built-in AWS
# IAM Policy "AWSGlueServiceRole" with some things obviously not needed removed
data "aws_iam_policy_document" "analytical_dataset_generation" {
  statement {
    effect = "Allow"

    actions = [
      "glue:*",
      "ec2:DescribeVpcEndpoints",
      "ec2:DescribeRouteTables",
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcAttribute",
      "iam:ListRolePolicies",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "cloudwatch:PutMetricData",
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:CreateBucket",
    ]

    resources = ["arn:aws:s3:::aws-glue-*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = [
      "arn:aws:s3:::aws-glue-*/*",
      "arn:aws:s3:::*/*aws-glue-*/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "arn:aws:s3:::crawler-public*",
      "arn:aws:s3:::aws-glue-*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:*:*:/aws-glue/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ec2:CreateTags",
      "ec2:DeleteTags",
    ]

    resources = [
      "arn:aws:ec2:*:*:network-interface/*",
      "arn:aws:ec2:*:*:security-group/*",
      "arn:aws:ec2:*:*:instance/*",
    ]

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"

      values = [
        "aws-glue-service-resource",
      ]
    }
  }
}

data "aws_iam_policy_document" "analytical_dataset_generation_s3" {
  statement {
    sid    = "analytical_dataset_generationListBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket*",
    ]

    resources = [
      aws_s3_bucket.published.arn,
      data.terraform_remote_state.common.config.bucket,
    ]
  }

  statement {
    sid    = "analytical_dataset_generationWriteBucket"
    effect = "Allow"

    actions = [
      "s3:DeleteObject*",
      "s3:GetObject*",
      "s3:PutObject*",
      "s3:GetBucketACL",
    ]

    resources = [
      "${aws_s3_bucket.published.arn}/business-data/manifest/*",
      "${aws_s3_bucket.published.arn}/business-data/manifest/",
      "${data.terraform_remote_state.common.config.bucket}/glue/scripts/*",
    ]
  }

  statement {
    sid    = "analytical_dataset_generationKMSEncrypt"
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]

    resources = [
      aws_kms_key.published_bucket_cmk.arn,
      data.terraform_remote_state.common.config.kms_key_id,
    ]
  }
}

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "analytical_dataset_generation" {
  name               = "AWSGlueServiceRole_analytical_dataset_generation"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
  tags               = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_policy" "analytical_dataset_generation" {
  name        = "analytical_dataset_generation"
  description = "Allows AWS Glue access to required AWS Resources"
  policy      = data.aws_iam_policy_document.analytical_dataset_generation.json
}

resource "aws_iam_policy" "analytical_dataset_generation_s3" {
  name        = "analytical_dataset_generation_s3"
  description = "Allows write access to the Manifest ETL bucket"
  policy      = data.aws_iam_policy_document.analytical_dataset_generation_s3.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generation" {
  role       = aws_iam_role.analytical_dataset_generation.name
  policy_arn = aws_iam_policy.analytical_dataset_generation.arn
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generation_s3" {
  role       = aws_iam_role.analytical_dataset_generation.name
  policy_arn = aws_iam_policy.analytical_dataset_generation_s3.arn
}

data "template_file" "analytical_dataset_generation_script_template" {
  template = "${file("files/manifest_comparison/aws_glue_script.py.tpl")}"

  vars = {
    database_name           = "aws_glue_catalog_database.analytical_dataset_generation.name"
    table_name_import_csv   = "import_csv"
    table_name_export_csv   = "export_csv"
    table_name_parquet      = "manifest_combined_parquet"
  }
}

resource "aws_s3_bucket_object" "analytical_dataset_generation_script" {
  bucket     = data.terraform_remote_state.common.config.bucket
  key        = "/glue/scripts/${local.environment}_analytical_dataset_generation.py"
  content    = data.template_file.analytical_dataset_generation_script_template.rendered
  kms_key_id = data.terraform_remote_state.common.config.kms_key_id
}

data "local_file" "analytical_dataset_generation_script_template" {
  filename = "files/manifest_comparison/aws_glue_script.py.tpl"
}

resource "aws_glue_job" "analytical_dataset_generation_combined" {
  name     = "analytical_dataset_generation_combined"
  role_arn = aws_iam_role.analytical_dataset_generation.arn
  worker_type = "G.2X"
  number_of_workers = "10"
  tags = merge(
    local.tags,
    {
      glue_script_hash = md5(data.local_file.analytical_dataset_generation_script_template.content)
    },
  )

  command {
    script_location = "s3://${aws_s3_bucket_object.analytical_dataset_generation_script.bucket}${aws_s3_bucket_object.analytical_dataset_generation_script.key}"
  }
}

output "analytical_dataset_generation" {
  value = {
    job_name = "aws_glue_job.analytical_dataset_generation_combined.name"
  }
}
