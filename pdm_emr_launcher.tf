variable "pdm_emr_launcher_zip" {
  type = map(string)
  default = {
    base_path = ""
    version   = ""
  }
}

resource "aws_lambda_function" "pdm_cw_emr_launcher" {
  filename = "${var.pdm_emr_launcher_zip["base_path"]}/dataworks-pdm-emr-launcher-${var.pdm_emr_launcher_zip["version"]}.zip"
  //  calling this pdm-emr-late-launcher because we already have a function called pdm-emr-launcher, can change this after we are sure that this works
  function_name = local.pdm_lambda_launcher_name
  role          = aws_iam_role.pdm_emr_launcher_lambda_role.arn
  handler       = "event_handler.handler"
  runtime       = "python3.8"
  source_code_hash = filebase64sha256(
    format(
      "%s/dataworks-pdm-emr-launcher-%s.zip",
      var.pdm_emr_launcher_zip["base_path"],
      var.pdm_emr_launcher_zip["version"]
    )
  )
  publish = false
  timeout = 60

  environment {
    variables = {
      SNS_TOPIC  = aws_sns_topic.adg_completion_status_sns.arn
      TABLE_NAME = local.data_pipeline_metadata
      LOG_LEVEL  = "debug"
    }
  }
}

resource "aws_cloudwatch_event_rule" "pdm_cw_emr_launcher_schedule" {
  name                = "pdm_cw_emr_launcher_schedule"
  description         = "Triggers PDM EMR Launcher everyday at 7pm"
  schedule_expression = format("cron(%s)", local.pdm_cw_emr_lambda_schedule[local.environment])
}

resource "aws_cloudwatch_event_target" "pdm_emr_launcher_target" {
  rule      = aws_cloudwatch_event_rule.pdm_cw_emr_launcher_schedule.name
  target_id = "pdm_cw_emr_launcher_target"
  arn       = aws_lambda_function.pdm_cw_emr_launcher.arn
}


resource "aws_iam_role" "pdm_emr_launcher_lambda_role" {
  name               = "pdm_cw_emr_launcher_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.pdm_emr_launcher_assume_policy.json
}

resource "aws_lambda_permission" "pdm_emr_relauncher_invoke_permission" {
  statement_id  = "AllowExecutionFromCloudWatchPDMEMRLauncher"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pdm_cw_emr_launcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.pdm_cw_emr_launcher_schedule.arn
}

data "aws_iam_policy_document" "pdm_emr_launcher_assume_policy" {
  statement {
    sid     = "PDMEMRLauncherLambdaAssumeRolePolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
  }
}

data "aws_iam_policy_document" "pdm_emr_launcher_scan_dynamo_policy" {
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

data "aws_iam_policy_document" "pdm_emr_launcher_sns_policy" {
  statement {
    sid    = "AllowAccessToSNSLauncherTopic"
    effect = "Allow"

    actions = [
      "sns:Publish",
    ]

    resources = [
      aws_sns_topic.adg_completion_status_sns.arn
    ]
  }
}


resource "aws_iam_policy" "pdm_emr_launcher_scan_dynamo_policy" {
  name        = "PDMEmrLauncherScanDynamoDb"
  description = "Allow PDM EMR launcher to scan pipeline metadata table"
  policy      = data.aws_iam_policy_document.pdm_emr_launcher_scan_dynamo_policy.json
}


resource "aws_iam_policy" "pdm_emr_launcher_sns_policy" {
  name        = "PDMEmrLauncherPublishSNSMessag"
  description = "Allow PDM EMR launcher to publish SNS message"
  policy      = data.aws_iam_policy_document.pdm_emr_launcher_sns_policy.json
}

resource "aws_iam_role_policy_attachment" "pdm_emr_launcher_policy_execution" {
  role       = aws_iam_role.pdm_emr_launcher_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pdm_emr_launcher_sns_attachment" {
  role       = aws_iam_role.pdm_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.pdm_emr_launcher_sns_policy.arn
}

resource "aws_iam_role_policy_attachment" "pdm_emr_launcher_scan_dynamo_attachment" {
  role       = aws_iam_role.pdm_emr_launcher_lambda_role.name
  policy_arn = aws_iam_policy.pdm_emr_launcher_scan_dynamo_policy.arn
}

