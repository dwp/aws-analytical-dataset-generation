variable "adg_emr_launcher_zip" {
  type = map(string)

  default = {
    base_path = ""
    version   = ""
  }
}

resource "aws_lambda_function" "adg_emr_launcher" {
  filename      = "${var.adg_emr_launcher_zip["base_path"]}/emr-launcher-${var.adg_emr_launcher_zip["version"]}.zip"
  function_name = "adg_emr_launcher"
  role          = aws_iam_role.adg_emr_launcher_lambda_role.arn
  handler       = "emr_launcher.handler"
  runtime       = "python3.7"
  source_code_hash = filebase64sha256(
  format(
  "%s/emr-launcher-%s.zip",
  var.adg_emr_launcher_zip["base_path"],
  var.adg_emr_launcher_zip["version"]
  )
  )
  publish = false
  timeout = 60

  environment {
    variables = {
      EMR_LAUNCHER_CONFIG_DIR = "docs/examples"
      EMR_LAUNCHER_LOG_LEVEL = "debug"
    }
  }
}

resource "aws_iam_role" "adg_emr_launcher_lambda_role" {
  name               = "adg_emr_launcher_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.adg_emr_launcher_assume_policy.json
}

data "aws_iam_policy_document" "adg_emr_launcher_assume_policy" {
  statement {
    sid    = "ADGEmrLauncherLambdaAssumeRolePolicy"
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type = "Service"
    }
  }
}

data "aws_iam_policy_document" "adg_emr_launcher_read_secret_policy" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      data.aws_secretsmanager_secret.secret.arn
    ]
  }
}

data "aws_secretsmanager_secret" "secret" {
  name = "EMR-Launcher-Payload"
}

data "aws_iam_policy_document" "adg_emr_launcher_runjobflow_policy" {
  statement {
    effect = "Allow"
    actions = [
      "elasticmapreduce:RunJobFlow",
    ]
    resources = [
      "*"
    ]
  }
}

data "aws_iam_policy_document" "adg_emr_launcher_pass_role_document" {
  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      "arn:aws:iam::*:role/*"
    ]
  }
}


resource "aws_iam_policy" "adg_emr_launcher_read_secrets_policy" {
  name        = "ADGReadSecrets"
  description = "Allow ADG to read secrets"
  policy      = data.aws_iam_policy_document.adg_emr_launcher_read_secret_policy.json
}

resource "aws_iam_policy" "adg_emr_launcher_runjobflow_policy" {
  name        = "ADGRunJobFlow"
  description = "Allow ADG to run job flow"
  policy      = data.aws_iam_policy_document.adg_emr_launcher_runjobflow_policy.json
}

resource "aws_iam_policy" "adg_emr_launcher_pass_role_policy" {
  name        = "ADGPassRole"
  description = "Allow ADG to pass role"
  policy      = data.aws_iam_policy_document.adg_emr_launcher_pass_role_document.json
}

resource "aws_iam_role_policy_attachment" "adg_emr_launcher_read_secrets_attachment" {
  role       = aws_iam_role.adg_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_launcher_read_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_launcher_runjobflow_attachment" {
  role       = aws_iam_role.adg_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_launcher_runjobflow_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_launcher_pass_role_attachment" {
  role       = aws_iam_role.adg_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_launcher_pass_role_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_launcher_policy_execution" {
  role       = aws_iam_role.adg_emr_launcher_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
