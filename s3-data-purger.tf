variable "s3_data_purger_zip" {
  type = map(string)

  default = {
    base_path = ""
    version   = ""
  }
}

resource "aws_lambda_function" "s3_data_purger" {
  filename      = "${var.s3_data_purger_zip["base_path"]}/emr-launcher-${var.s3_data_purger_zip["version"]}.zip"
  function_name = "s3_data_purger"
  role          = aws_iam_role.s3_data_purger_lambda_role.arn
  handler       = "s3_data_purger.handler"
  runtime       = "python3.7"
  source_code_hash = filebase64sha256(
    format(
      "%s/s3-data-purger-%s.zip",
      var.s3_data_purger_zip["base_path"],
      var.s3_data_purger_zip["version"]
    )
  )
  publish = false
  timeout = 60

  environment {
    variables = {
      S3_DATA_PURGER_LOG_LEVEL        = "debug"
    }
  }
}


resource "aws_iam_role" "s3_data_purger_lambda_role" {
  name               = "s3_data_purger_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.s3_data_purger_assume_policy.json
}

data "aws_iam_policy_document" "s3_data_purger_assume_policy" {
  statement {
    sid     = "S3DataPurgerLambdaAssumeRolePolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
  }
}
resource "aws_cloudwatch_event_rule" "s3_data_purger_rule" {
  name                = "s3_data_purger_rule"
  description         = "Triggers S3 data purger lambda"
  schedule_expression = format("cron(%s)", local.s3_data_purger_schedule[local.environment])
}

resource "aws_cloudwatch_event_target" "s3_data_purger_target" {
  rule      = aws_cloudwatch_event_rule.s3_data_purger_rule.name
  target_id = "s3_data_purger_target"
  arn       = aws_lambda_function.s3_data_purger.arn
}
resource "aws_lambda_permission" "s3_data_purger_invoke_permission" {
  statement_id  = "AllowExecutionFromS3DataPurger"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_data_purger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adg_emr_launcher_schedule.arn
}


data "aws_iam_policy_document" "s3_data_purger_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:DeleteObject"
    ]
    resources = [
      aws_s3_bucket.published.arn
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      "${aws_kms_key.published_bucket_cmk.arn}"
    ]
  }
  statement {
    sid    = "AllowS3DataPurgerAccessToDataPipelineMetadataDynamoDb"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:GetRecords",
      "dynamodb:Query"
    ]

    resources = [data.terraform_remote_state.internal_compute.outputs.data_pipeline_metadata_dynamo.arn]
  }
}

resource "aws_iam_policy" "s3_data_purger_delete_s3_policy" {
  name        = "s3_data_purger_delete_s3_policy"
  description = "Data purger of S3 bucket"
  policy      = data.aws_iam_policy_document.s3_data_purger_policy.json
}


resource "aws_iam_role_policy_attachment" "s3_data_purger_policy_attachment" {
  role       = aws_iam_role.s3_data_purger_lambda_role.name
  policy_arn = aws_iam_policy.s3_data_purger_delete_s3_policy.arn
}


resource "aws_iam_role_policy_attachment" "s3_data_purger_policy_execution" {
  role       = aws_iam_role.s3_data_purger_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}


