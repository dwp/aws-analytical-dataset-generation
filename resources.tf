data "aws_secretsmanager_secret" "adg_secret" {
  name = local.secret_name
}

data "aws_iam_policy_document" "analytical_dataset_secretsmanager" {
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

resource "aws_iam_policy" "analytical_dataset_secretsmanager" {
  name        = "DatasetGeneratorSecretsManager"
  description = "Allow Dataset Generator clusters to get secrets"
  policy      = data.aws_iam_policy_document.analytical_dataset_secretsmanager.json
}

resource "aws_iam_role_policy_attachment" "emr_analytical_dataset_secretsmanager" {
  role       = aws_iam_role.analytical_dataset_generator.name
  policy_arn = aws_iam_policy.analytical_dataset_secretsmanager.arn
}


