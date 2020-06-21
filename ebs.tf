data "aws_iam_policy_document" "adg_ebs_cmk" {
  statement {
    sid    = "Enable access control with IAM policies"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account[local.environment]}:root"]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }
}

resource "aws_kms_key" "adg_ebs_cmk" {
  description             = "Encrypts ADG EBS volumes"
  deletion_window_in_days = 7
  is_enabled              = true
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.adg_ebs_cmk.json


  tags = merge(
    local.tags,
    {
      Name                  = "adg_ebs_cmk"
      ProtectsSensitiveData = "True"
    }
  )
}

resource "aws_kms_alias" "adg_ebs_cmk" {
  name          = "alias/adg_ebs_cmk"
  target_key_id = aws_kms_key.adg_ebs_cmk.key_id
}

data "aws_iam_policy_document" "analytical_dataset_ebs_cmk_encrypt" {
  statement {
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]

    resources = [aws_kms_key.adg_ebs_cmk.arn]
  }

  statement {
    effect = "Allow"

    actions = ["kms:CreateGrant"]

    resources = [aws_kms_key.adg_ebs_cmk.arn]
    condition {
      test     = "Bool"
      variable = "kms:GrantIsForAWSResource"
      values   = ["true"]
    }
  }
}

resource "aws_iam_policy" "analytical_dataset_ebs_cmk_encrypt" {
  name        = "AnalyticalDatasetGeneratorEbsCmkEncrypt"
  description = "Allow encryption and decryption using the Analytical Dataset Generator EBS CMK"
  policy      = data.aws_iam_policy_document.analytical_dataset_ebs_cmk_encrypt.json
}
