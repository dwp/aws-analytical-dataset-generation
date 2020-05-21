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

resource "aws_s3_bucket_object" "cluster" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/cluster.yaml"
  content    = data.template_file.cluster.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "instances" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/instances.yaml"
  content    = data.template_file.instances.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "steps" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/steps.yaml"
  content    = data.template_file.steps.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
}

resource "aws_s3_bucket_object" "configurations" {
  bucket     = data.terraform_remote_state.common.outputs.config_bucket.id
  key        = "emr/adg/configurations.yaml"
  content    = data.template_file.configurations.rendered
  kms_key_id = data.terraform_remote_state.common.outputs.config_bucket_cmk.arn
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

data "template_file" "cluster" {
  template = file("emr/adg/cluster.yaml.tpl")

  vars = {
    s3_log_bucket    = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
    s3_log_prefix    = local.s3_log_prefix
    ami_id           = var.emr_ami_id
    service_role     = aws_iam_role.analytical_dataset_generator.arn
    instance_profile = aws_iam_instance_profile.analytical_dataset_generator.arn
  }
}

data "template_file" "configurations" {
  template = file("emr/adg/configurations.yaml.tpl")

  vars = {
    s3_log_bucket       = data.terraform_remote_state.security-tools.outputs.logstore_bucket.id
    s3_published_bucket = aws_s3_bucket.published.id
    s3_ingest_bucket    = data.terraform_remote_state.ingest.outputs.s3_buckets.input_bucket
    hbase_root_path     = local.hbase_root_path
    proxy_no_proxy      = "169.254.169.254|*.s3.eu-west-2.amazonaws.com|s3.eu-west-2.amazonaws.com|sns.eu-west-2.amazonaws.com|sqs.eu-west-2.amazonaws.com|eu-west-2.queue.amazonaws.com|glue.eu-west-2.amazonaws.com|sts.eu-west-2.amazonaws.com|*.eu-west-2.compute.internal|dynamodb.eu-west-2.amazonaws.com"
    proxy_http_address  = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.http_address
    proxy_https_address = data.terraform_remote_state.internet_egress.outputs.internet_proxy_service.https_address
  }
}

data "template_file" "instances" {
  template = file("emr/adg/instances.yaml.tpl")

  vars = {
    add_master_sg     = aws_security_group.analytical_dataset_generation.id
    add_slave_sg      = aws_security_group.analytical_dataset_generation.id
    subnet_id         = data.terraform_remote_state.internal_compute.outputs.htme_subnet.ids[0]
    master_sg         = aws_security_group.master_sg.id
    slave_sg          = aws_security_group.slave_sg.id
    service_access_sg = aws_security_group.service_access_sg.id
    instance_type     = var.emr_instance_type[local.environment]
  }
}

data "template_file" "steps" {
  template = file("emr/adg/steps.yaml.tpl")

  vars = {
    s3_config_bucket = data.terraform_remote_state.common.outputs.config_bucket.id
  }
}
