data "aws_secretsmanager_secret" "adg_secret_full" {
  name = local.secret_name_full
}

data "aws_secretsmanager_secret" "adg_secret_incremental" {
  name = local.secret_name_incremental
}

data "aws_iam_policy_document" "analytical_dataset_secretsmanager" {
  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      data.aws_secretsmanager_secret.adg_secret_full.arn,
      data.aws_secretsmanager_secret.adg_secret_incremental.arn
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_secretsmanager" {
  name        = "DatasetGeneratorSecretsManager"
  description = "Allow reading of ADG config values"
  policy      = data.aws_iam_policy_document.analytical_dataset_secretsmanager.json
}
