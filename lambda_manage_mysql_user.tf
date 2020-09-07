variable "manage_mysql_user_lambda_zip" {
  type = map(string)

  default = {
    base_path = ""
    version   = ""
  }
}

data "aws_iam_policy_document" "lambda_assume_policy" {
  statement {
    sid    = "LambdaApiAssumeRolePolicy"
    effect = "Allow"

    actions = [
      "sts:AssumeRole",
    ]

    principals {
      identifiers = [
        "lambda.amazonaws.com",
      ]

      type = "Service"
    }
  }
}

resource "aws_iam_role" "lambda_manage_mysql_user_adg" {
  name               = "lambda_manage_mysql_user_adg"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_policy.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_manage_mysql_user_vpcaccess" {
  role       = aws_iam_role.lambda_manage_mysql_user_adg.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "lambda_manage_mysql_user_adg" {
  statement {
    sid    = "AllowUpdatePassword"
    effect = "Allow"

    actions = [
      "secretsmanager:PutSecretValue",
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      aws_secretsmanager_secret.metadata_store_master.arn,
      aws_secretsmanager_secret.metadata_store_datareader.arn,
    ]
  }
}

resource "aws_iam_role_policy" "lambda_manage_mysql_user_adg" {
  role   = aws_iam_role.lambda_manage_mysql_user_adg.name
  policy = data.aws_iam_policy_document.lambda_manage_mysql_user_adg.json
}

resource "aws_lambda_function" "manage_mysql_user" {
  filename      = "${var.manage_mysql_user_lambda_zip["base_path"]}/manage-mysql-user-${var.manage_mysql_user_lambda_zip["version"]}.zip"
  function_name = "manage-mysql-user"
  role          = aws_iam_role.lambda_manage_mysql_user_adg.arn
  handler       = "manage-mysql-user.handler"
  runtime       = "python3.7"
  source_code_hash = filebase64sha256(
    format(
      "%s/manage-mysql-user-%s.zip",
      var.manage_mysql_user_lambda_zip["base_path"],
      var.manage_mysql_user_lambda_zip["version"],
    ),
  )
  publish = false

  vpc_config {
    subnet_ids = data.terraform_remote_state.internal_compute.outputs.pdm_subnet.ids
    security_group_ids = [aws_security_group.adg_common.id]
  }

  timeout                        = 300
  reserved_concurrent_executions = 1

  environment {
    variables = {
      RDS_ENDPOINT                    = aws_rds_cluster.hive_metastore.endpoint
      RDS_DATABASE_NAME               = aws_rds_cluster.hive_metastore.database_name
      RDS_MASTER_USERNAME             = var.metadata_store_master_username
      RDS_MASTER_PASSWORD_SECRET_NAME = aws_secretsmanager_secret.metadata_store_master.name
      RDS_CA_CERT                     = "/var/task/AmazonRootCA1.pem" # For Aurora serverless
      LOG_LEVEL                       = "DEBUG"
    }
  }

  tracing_config {
    mode = "PassThrough"
  }

  tags = merge(
    local.common_tags,
    {
      "Name" = "manage-mysql-user"
    },
    {
      "ProtectsSensitiveData" = "False"
    },
  )

  depends_on = [aws_cloudwatch_log_group.manage_mysql_user_adg]
}

resource "aws_cloudwatch_log_group" "manage_mysql_user_adg" {
  name              = "/aws/lambda/manage-mysql-user_adg"
  retention_in_days = 180
}
