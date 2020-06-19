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

resource "aws_iam_role" "analytical_dataset_generator" {
  name               = "analytical_dataset_generator"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.tags
}

resource "aws_iam_instance_profile" "analytical_dataset_generator" {
  name = "analytical_dataset_generator"
  role = aws_iam_role.analytical_dataset_generator.id
}

resource "aws_iam_role_policy_attachment" "ec2_for_ssm_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_role_policy_attachment" "amazon_ssm_managed_instance_core" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_write_parquet" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_write_parquet.arn
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_gluetables" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_gluetables_write.arn
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_acm" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_acm.arn
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_secretsmanager" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_secretsmanager.arn
}

data "aws_iam_policy_document" "analytical_dataset_generator_write_logs" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.security-tools.outputs.logstore_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
      "s3:PutObject*",

    ]

    resources = [
      "${data.terraform_remote_state.security-tools.outputs.logstore_bucket.arn}/${local.s3_log_prefix}",
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
      data.terraform_remote_state.security-tools.outputs.logstore_bucket.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_write_logs" {
  name        = "AnalyticalDatasetGeneratorWriteLogs"
  description = "Allow writing of Analytical Dataset logs"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_write_logs.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_write_logs" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_write_logs.arn
}

data "aws_iam_policy_document" "analytical_dataset_generator_read_config" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.config_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.config_bucket.arn}/*",
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
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_read_config" {
  name        = "AnalyticalDatasetGeneratorReadConfig"
  description = "Allow reading of Analytical Dataset config files"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_read_config.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_read_config" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_read_config.arn
}

data "aws_iam_policy_document" "analytical_dataset_generator_read_artefacts" {
  statement {
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
    ]

    resources = [
      "${data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn}/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.management_artefact.outputs.artefact_bucket.cmk_arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_read_artefacts" {
  name        = "AnalyticalDatasetGeneratorReadArtefacts"
  description = "Allow reading of Analytical Dataset software artefacts"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_read_artefacts.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_read_artefacts" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_read_artefacts.arn
}
