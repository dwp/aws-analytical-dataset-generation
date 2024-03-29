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

resource "aws_iam_role_policy_attachment" "ec2_for_ssm_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_role_policy_attachment" "amazon_ssm_managed_instance_core" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_ebs_cmk" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_ebs_cmk_encrypt.arn
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

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_read_write_processed_bucket" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.adg_read_write_processed_bucket.arn
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
      data.terraform_remote_state.common.outputs.config_bucket_cmk.arn,
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

data "aws_iam_policy_document" "analytical_dataset_generator_write_dynamodb" {
  statement {
    effect = "Allow"

    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:GetRecords",
      "dynamodb:Query",
    ]

    resources = [
      data.terraform_remote_state.internal_compute.outputs.uc_export_crown_dynamodb_table.arn,
      data.terraform_remote_state.internal_compute.outputs.data_pipeline_metadata_dynamo.arn
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_write_dynamodb" {
  name        = "AnalyticalDatasetGeneratorDynamoDB"
  description = "Allows read and write access to ADG's EMRFS DynamoDB table"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_write_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_dynamodb" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_write_dynamodb.arn
}

data "aws_iam_policy_document" "analytical_dataset_generator_metadata_change" {
  statement {
    effect = "Allow"

    actions = [
      "ec2:ModifyInstanceMetadataOptions",
      "ec2:*Tags",
    ]

    resources = [
      "arn:aws:ec2:${var.region}:${local.account[local.environment]}:instance/*",
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_metadata_change" {
  name        = "AnalyticalDatasetGeneratorMetadataOptions"
  description = "Allow editing of Metadata Options"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_metadata_change.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_metadata_change" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_metadata_change.arn
}

data "aws_iam_policy_document" "analytical_dataset_generator_read_htme" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      format("arn:aws:s3:::%s", data.terraform_remote_state.internal_compute.outputs.htme_s3_bucket.id),
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject*",
    ]

    resources = [
      format("arn:aws:s3:::%s/%s/*", data.terraform_remote_state.internal_compute.outputs.htme_s3_bucket.id, data.terraform_remote_state.internal_compute.outputs.htme_s3_folder.id)
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.internal_compute.outputs.compaction_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_read_htme" {
  name        = "AnalyticalDatasetGeneratorReadHTMEOutputFiles"
  description = "Allow reading of HTME output files"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_read_htme.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_read_htme" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_read_htme.arn
}

resource "aws_iam_policy" "analytical_dataset_generator_publish_sns" {
  name        = "AnalyticalDatasetGeneratorPublishSns"
  description = "Allow ADG to publish SNS messages"
  policy      = data.aws_iam_policy_document.adg_sns_topic_policy_for_completion_status.json
}

resource "aws_iam_role_policy_attachment" "analytical_dataset_generator_publish_sns" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_generator_publish_sns.arn
}

data "aws_iam_policy_document" "adg_sns_topic_policy_for_completion_status" {
  statement {
    sid = "AdgCompletionStatusSns"

    actions = [
      "SNS:Publish",
    ]

    effect = "Allow"

    resources = [
      aws_sns_topic.adg_completion_status_sns.arn,
      data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn,
    ]
  }
}

resource "aws_iam_policy" "adg_cloudwatch_topic_policy_for_pdm_trigger" {
  name        = "AdgPDMTrigger"
  description = "Allow ADG to publish Cloudwatch rules and targets"
  policy      = data.aws_iam_policy_document.adg_cloudwatch_topic_policy_for_pdm_trigger.json
}

resource "aws_iam_role_policy_attachment" "adg_cloudwatch_topic_policy_for_pdm_trigger" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.adg_cloudwatch_topic_policy_for_pdm_trigger.arn
}

data "aws_iam_policy_document" "adg_cloudwatch_topic_policy_for_pdm_trigger" {
  statement {
    sid = "AdgPDMTriggerPolicy"

    actions = [
      "events:EnableRule",
      "events:PutRule",
      "events:PutTargets",
      "events:ListRules",
      "events:DeleteRule",
      "events:ListTargetsByRule",
      "events:RemoveTargets",
    ]

    effect = "Allow"

    resources = ["*"]
  }
}
