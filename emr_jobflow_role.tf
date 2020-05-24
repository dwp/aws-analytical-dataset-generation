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

resource "aws_iam_role_policy_attachment" "emr_for_ec2_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"

}

resource "aws_iam_role_policy_attachment" "ec2_for_ssm_attachment" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"

}

resource "aws_iam_role_policy_attachment" "use_ebs_cmk" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_ebs_cmk_encrypt.arn
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

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_acm" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_acm.arn
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

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_secretsmanager" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_secretsmanager.arn
}
