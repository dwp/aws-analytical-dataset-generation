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

resource "aws_iam_role" "analytical_dataset_generator" {
  name               = "analytical_dataset_generator"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.tags
}

resource "aws_iam_instance_profile" "analytical_dataset_generator" {
  name = "analytical_dataset_generator"
  role = aws_iam_role.analytical_dataset_generator.id
}

resource "aws_iam_role_policy_attachment" "adg_ec2_for_ssm_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"

}

resource "aws_iam_role_policy_attachment" "adg_amazon_ssm_managed_instance_core" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.analytical_dataset_generator.name
}

data "aws_iam_policy_document" "analytical_dataset_gluetables" {
  statement {
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
    ]

    resources = [
      "arn:aws:glue:::database/${aws_glue_catalog_database.analytical_dataset_generation_staging.name}",
      "arn:aws:glue:::database/${aws_glue_catalog_database.analytical_dataset_generation.name}",
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_gluetables" {
  name        = "AnalyticalDatasetGeneratorGlueTables"
  description = "Allow Dataset Generator clusters to create drop tables"
  policy      = data.aws_iam_policy_document.analytical_dataset_gluetables.json
}

resource "aws_iam_role_policy_attachment" "adg_analytical_dataset_gluetables" {
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
  name        = "AnalyticalDatasetGeneratorACM"
  description = "Allow export of ADG's ACM certificcate"
  policy      = data.aws_iam_policy_document.analytical_dataset_acm.json
}

resource "aws_iam_role_policy_attachment" "adg_analytical_dataset_acm" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_acm.arn
}

data "aws_iam_policy_document" "read_ingest_hbase" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      "arn:aws:s3:::${data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket}",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
    ]

    resources = [
      "arn:aws:s3:::${data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket}/${data.terraform_remote_state.ingest.outputs.s3_buckets.hbase_rootdir}/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      "${data.terraform_remote_state.ingest.outputs.input_bucket_cmk.arn}",
    ]
  }
}

resource "aws_iam_policy" "read_ingest_hbase" {
  name        = "IngestHBaseRead"
  description = "Allow read only access to Ingest HBase data"
  policy      = data.aws_iam_policy_document.read_ingest_hbase.json
}

resource "aws_iam_role_policy_attachment" "adg_read_ingest_hbase" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.read_ingest_hbase.arn
}

data "aws_iam_policy_document" "write_analytical_dataset" {

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
      "s3:PutObject*",
    ]

    resources = [
      "${aws_s3_bucket.published.arn}/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey*",
      "kms:ReEncrypt*",
    ]

    resources = [
      "${aws_kms_key.published_bucket_cmk.arn}",
    ]
  }
}
resource "aws_iam_policy" "write_analytical_dataset" {
  name        = "AnalyticalDatasetWriteData"
  description = "Allow write access to the Analytical Dataset"
  policy      = data.aws_iam_policy_document.write_analytical_dataset.json
}

resource "aws_iam_role_policy_attachment" "adg_write_analytical_dataset" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.write_analytical_dataset.arn
}

data "aws_iam_policy_document" "write_analytical_dataset_logs" {
  statement {
    effect = "Allow"

    actions = [
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
      "${data.terraform_remote_state.security-tools.outputs.logstore_bucket.arn}/${local.s3_log_prefix}/*"
    ]
  }
}

resource "aws_iam_policy" "write_analytical_dataset_logs" {
  name        = "AnalyticalDatasetWriteLogs"
  description = "Allow write access to the Analytical Dataset Logs"
  policy      = data.aws_iam_policy_document.write_analytical_dataset_logs.json
}

resource "aws_iam_role_policy_attachment" "adg_write_analytical_dataset_logs" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.write_analytical_dataset_logs.arn
}

data "aws_iam_policy_document" "read_analytical_dataset_config" {
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
      "${data.terraform_remote_state.common.outputs.config_bucket.arn}/component/analytical-dataset-generation/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:DescribeKey",
      "kms:Decrypt",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.config_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "read_analytical_dataset_config" {
  name        = "AnalyticalDatasetReadConfig"
  description = "Allow read access to the Analytical Dataset Config"
  policy      = data.aws_iam_policy_document.read_analytical_dataset_config.json
}

resource "aws_iam_role_policy_attachment" "adg_read_analytical_dataset_config" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.read_analytical_dataset_config.arn
}

data "aws_iam_policy_document" "read_analytical_dataset_artefacts" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${data.terraform_remote_state.management_artefact.outputs.artefact_bucket.arn}/*"
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

resource "aws_iam_policy" "read_analytical_dataset_artefacts" {
  name        = "AnalyticalDatasetReadArtefacts"
  description = "Allow read access to Analytical Dataset software artefacts"
  policy      = data.aws_iam_policy_document.read_analytical_dataset_artefacts.json
}

resource "aws_iam_role_policy_attachment" "adg_read_analytical_dataset_artefacts" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.read_analytical_dataset_artefacts.arn
}

data "aws_secretsmanager_secret" "adg_secret" {
  name = local.secret_name
}

data "aws_iam_policy_document" "read_analytical_dataset_secrets" {
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

resource "aws_iam_policy" "read_analytical_dataset_secrets" {
  name        = "AnalyticalDatasetReadSecrets"
  description = "Allow read access to Analytical Dataset Generator secrets"
  policy      = data.aws_iam_policy_document.read_analytical_dataset_secrets.json
}

resource "aws_iam_role_policy_attachment" "adg_read_analytical_dataset_secrets" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.read_analytical_dataset_secrets.arn
}

