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
      EMR_LAUNCHER_CONFIG_S3_BUCKET = data.terraform_remote_state.common.outputs.config_bucket.id
      EMR_LAUNCHER_CONFIG_S3_FOLDER = "emr/adg"
      EMR_LAUNCHER_LOG_LEVEL        = "debug"
    }
  }
}

resource "aws_cloudwatch_event_rule" "adg_emr_launcher_schedule" {
  name                = "adg_emr_launcher_schedule"
  description         = "Triggers ADG EMR Launcher"
  schedule_expression = format("cron(%s)", local.adg_emr_lambda_schedule[local.environment])
}

resource "aws_cloudwatch_event_target" "adg_emr_launcher_target" {
  rule      = aws_cloudwatch_event_rule.adg_emr_launcher_schedule.name
  target_id = "adg_emr_launcher_target"
  arn       = aws_lambda_function.adg_emr_launcher.arn
}

resource "aws_iam_role" "adg_emr_launcher_lambda_role" {
  name               = "adg_emr_launcher_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.adg_emr_launcher_assume_policy.json
}

resource "aws_lambda_permission" "adg_emr_launcher_invoke_permission" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adg_emr_launcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adg_emr_launcher_schedule.arn
}

data "aws_iam_policy_document" "adg_emr_launcher_assume_policy" {
  statement {
    sid     = "ADGEMRLauncherLambdaAssumeRolePolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
  }
}

data "aws_iam_policy_document" "adg_emr_launcher_read_s3_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      format("arn:aws:s3:::%s/emr/adg/*", data.terraform_remote_state.common.outputs.config_bucket.id)
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
    ]
    resources = [
      data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
    ]
  }
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

resource "aws_iam_policy" "adg_emr_launcher_read_s3_policy" {
  name        = "ADGReadS3"
  description = "Allow ADG to read from S3 bucket"
  policy      = data.aws_iam_policy_document.adg_emr_launcher_read_s3_policy.json
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

resource "aws_iam_role_policy_attachment" "adg_emr_launcher_read_s3_attachment" {
  role       = aws_iam_role.adg_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_launcher_read_s3_policy.arn
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
