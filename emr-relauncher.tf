variable "dataworks_emr_relauncher_zip" {
  type = map(string)

  default = {
    base_path = ""
    version   = ""
  }
}

resource "aws_lambda_function" "adg_emr_relauncher" {
  filename      = "${var.adg_emr_relauncher_zip["base_path"]}/dataworks-emr-relauncher-${var.adg_emr_relauncher_zip["version"]}.zip"
  function_name = "adg_emr_relauncher"
  role          = aws_iam_role.adg_emr_relauncher_lambda_role.arn
  handler       = "event_handler.handler"
  runtime       = "python3.8"
  source_code_hash = filebase64sha256(
    format(
      "%s/dataworks-emr-relauncher-%s.zip",
      var.adg_emr_relauncher_zip["base_path"],
      var.adg_emr_relauncher_zip["version"]
    )
  )
  publish = false
  timeout = 60

  environment {
    variables = {
      SNS_TOPIC          = data.terraform_remote_state.internal_compute.outputs.export_status_sns_fulls.arn
      TABLE_NAME         = local.data_pipeline_metadata
      MAX_RETRY_COUNT    = local.adg_max_retry_count[local.environment]
      LOG_LEVEL          = "info"
    }
  }
}

resource "aws_cloudwatch_event_target" "adg_emr_relauncher_target_full" {
  rule      = aws_cloudwatch_event_rule.adg_full_failed.name
  target_id = "adg_emr_relauncher_target_full"
  arn       = aws_lambda_function.adg_emr_relauncher.arn
}

resource "aws_cloudwatch_event_target" "adg_emr_relauncher_target_incremental" {
  rule      = aws_cloudwatch_event_rule.adg_incremental_failed.name
  target_id = "adg_emr_relauncher_target_incremental"
  arn       = aws_lambda_function.adg_emr_relauncher.arn
}


resource "aws_iam_role" "adg_emr_relauncher_lambda_role" {
  name               = "adg_emr_relauncher_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.adg_emr_relauncher_assume_policy.json
}

resource "aws_lambda_permission" "adg_emr_relauncher_invoke_permission_full" {
  statement_id  = "AllowExecutionFromCloudWatchFull"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adg_emr_relauncher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adg_full_failed.arn
}

resource "aws_lambda_permission" "adg_emr_relauncher_invoke_permission_incremental" {
  statement_id  = "AllowExecutionFromCloudWatchIncremental"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adg_emr_relauncher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adg_incremental_failed.arn
}

data "aws_iam_policy_document" "adg_emr_relauncher_assume_policy" {
  statement {
    sid     = "adgEMRLauncherLambdaAssumeRolePolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
  }
}

data "aws_iam_policy_document" "adg_emr_relauncher_scan_dynamo_policy" {
  statement {
    effect = "Allow"

    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:Scan"
    ]

    resources = [
      "arn:aws:dynamodb:${var.region}:${local.account[local.environment]}:table/${local.data_pipeline_metadata}"
    ]
  }
}

data "aws_iam_policy_document" "adg_emr_relauncher_sns_policy" {
  statement {
    sid    = "AllowAccessToSNSLauncherTopic"
    effect = "Allow"

    actions = [
      "sns:Publish",
    ]

    resources = [
      data.terraform_remote_state.internal_compute.outputs.export_status_sns_fulls.arn
    ]
  }
}

data "aws_iam_policy_document" "adg_emr_relauncher_pass_role_document" {
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

resource "aws_iam_policy" "adg_emr_relauncher_scan_dynamo_policy" {
  name        = "AdgEmrRelauncherScanDynamoDb"
  description = "Allow Emr relauncher to scan pipeline metadata table"
  policy      = data.aws_iam_policy_document.adg_emr_relauncher_scan_dynamo_policy.json
}

resource "aws_iam_policy" "adg_emr_relauncher_sns_policy" {
  name        = "AdgEmrRelauncherSnsPublish"
  description = "Allow adg to run job flow"
  policy      = data.aws_iam_policy_document.adg_emr_relauncher_sns_policy.json
}

resource "aws_iam_policy" "adg_emr_relauncher_pass_role_policy" {
  name        = "AdgEmrRelauncherPassRole"
  description = "Allow Emr relauncher to publish messages to launcher topic"
  policy      = data.aws_iam_policy_document.adg_emr_relauncher_pass_role_document.json
}

resource "aws_iam_role_policy_attachment" "adg_emr_relauncher_pass_role_attachment" {
  role       = aws_iam_role.adg_emr_relauncher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_relauncher_pass_role_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_relauncher_policy_execution" {
  role       = aws_iam_role.adg_emr_relauncher_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "adg_emr_relauncher_sns_attachment" {
  role       = aws_iam_role.adg_emr_relauncher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_relauncher_sns_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_relauncher_scan_dynamo_attachment" {
  role       = aws_iam_role.adg_emr_relauncher_lambda_role.name
  policy_arn = aws_iam_policy.adg_emr_relauncher_scan_dynamo_policy.arn
}

