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



data "aws_iam_policy_document" "analytical_dataset_generator_write_parquet" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
      data.terraform_remote_state.common.outputs.published_bucket.arn,
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
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/analytical-dataset/*",
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
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_generator_write_parquet" {
  name        = "AnalyticalDatasetGeneratorWriteParquet"
  description = "Allow writing of Analytical Dataset parquet files"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_write_parquet.json
}

data "aws_iam_policy_document" "analytical_dataset_read_only" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:Get*",
      "s3:List*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/analytical-dataset/*",
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_read_only" {
  name        = "AnalyticalDatasetReadOnly"
  description = "Allow read access to the Analytical Dataset"
  policy      = data.aws_iam_policy_document.analytical_dataset_read_only.json
}

data "aws_iam_policy_document" "analytical_dataset_crown_read_only" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:Get*",
      "s3:List*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/analytical-dataset/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:ExistingObjectTag/collection_tag"

      values = [
        "crown"
      ]
    }
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_crown_read_only" {
  name        = "AnalyticalDatasetCrownReadOnly"
  description = "Allow read access to the Crown-specific subset of the Analytical Dataset"
  policy      = data.aws_iam_policy_document.analytical_dataset_crown_read_only.json
}

data "aws_iam_policy_document" "analytical_dataset_crown_read_only_non_pii" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:Get*",
      "s3:List*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/analytical-dataset/*",
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/aws-analytical-env-metrics-data/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:ExistingObjectTag/Pii"

      values = [
        "false"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "s3:ExistingObjectTag/collection_tag"

      values = [
        "crown"
      ]

    }
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_crown_read_only_non_pii" {
  name        = "AnalyticalDatasetCrownReadOnlyNonPii"
  description = "Allow read access to the Crown-specific subset of the Analytical Dataset"
  policy      = data.aws_iam_policy_document.analytical_dataset_crown_read_only_non_pii.json
}

resource "aws_iam_policy" "analytical_dataset_generator_read_write_non_pii" {
  name        = "AnalyticalDatasetGeneratorReadWriteNonPii"
  description = "Allow read writing of non-pii data"
  policy      = data.aws_iam_policy_document.analytical_dataset_generator_read_write_non_pii.json
}

# policy for s3 read access of both non-pii and pii PDM data

data "aws_iam_policy_document" "pdm_read_pii_and_non_pii" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:Get*",
      "s3:List*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/pdm-dataset/*",
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/aws-analytical-env-metrics-data/*",
    ]

  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "pdm_read_pii_and_non_pii" {
  name        = "ReadPDMPiiAndNonPii"
  description = "Allow read access to the PDM tables"
  policy      = data.aws_iam_policy_document.pdm_read_pii_and_non_pii.json
}

# policy for s3 read access of non-pii PDM data only

data "aws_iam_policy_document" "pdm_read_non_pii_only" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:Get*",
      "s3:List*",
    ]

    resources = [
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/pdm-dataset/*",
      "${data.terraform_remote_state.common.outputs.published_bucket.arn}/aws-analytical-env-metrics-data/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:ExistingObjectTag/pii"

      values = [
        "false"
      ]
    }

  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]

    resources = [
      data.terraform_remote_state.common.outputs.published_bucket_cmk.arn,
    ]
  }
}

resource "aws_iam_policy" "pdm_read_non_pii_only" {
  name        = "ReadPDMNonPiiOnly"
  description = "Allow read access to a subset of the PDM tables containing less sensitive data called non-pii"
  policy      = data.aws_iam_policy_document.pdm_read_non_pii_only.json
}

output "published_bucket_cmk" {
  value = data.terraform_remote_state.common.outputs.published_bucket_cmk
}

output "published_bucket" {
  value = data.terraform_remote_state.common.outputs.published_bucket
}
