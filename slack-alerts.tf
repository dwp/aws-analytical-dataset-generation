resource "aws_cloudwatch_event_rule" "adg_terminated_with_errors_rule" {
  name          = "adg_terminated_with_errors_rule"
  description   = "Sends failed message to slack when adg cluster terminates with errors"
  event_pattern = <<EOF
{
  "source": [
    "aws.emr"
  ],
  "detail-type": [
    "EMR Cluster State Change"
  ],
  "detail": {
    "state": [
      "TERMINATED_WITH_ERRORS"
    ],
    "name": [
      "analytical-dataset-generator-full"
    ]
  }
}
EOF
}

resource "aws_cloudwatch_metric_alarm" "adg_failed_with_errors" {
  alarm_name                = "adg_failed_with_errors"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "1"
  metric_name               = "TriggeredRules"
  namespace                 = "AWS/Events"
  period                    = "60"
  statistic                 = "Sum"
  threshold                 = "1"
  alarm_description         = "This metric monitors cluster termination with errors"
  insufficient_data_actions = []
  alarm_actions             = [data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn]
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.adg_terminated_with_errors_rule.name
  }
  tags = merge(
    local.common_tags,
    {
      Name              = "adg_failed_with_errors",
      notification_type = "Error",
      severity          = "Critical"
    },
  )
}

resource "aws_cloudwatch_event_rule" "adg_success" {
  name          = "adg_success"
  description   = "checks that all steps complete"
  event_pattern = <<EOF
{
  "source": [
    "aws.emr"
  ],
  "detail-type": [
    "EMR Cluster State Change"
  ],
  "detail": {
    "state": [
      "TERMINATED"
    ],
    "name": [
      "analytical-dataset-generator-full"
    ],
    "stateChangeReason": [
      "{\"code\":\"ALL_STEPS_COMPLETED\",\"message\":\"Steps completed\"}"
    ]
  }
}
EOF
}


resource "aws_cloudwatch_metric_alarm" "adg_success" {
  alarm_name                = "adg_completed_all_steps"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "1"
  metric_name               = "TriggeredRules"
  namespace                 = "AWS/Events"
  period                    = "60"
  statistic                 = "Sum"
  threshold                 = "1"
  alarm_description         = "Monitoring adg full completion"
  insufficient_data_actions = []
  alarm_actions             = [data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn]
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.adg_success.name
  }
  tags = merge(
    local.common_tags,
    {
      Name              = "adg_success",
      notification_type = "Information",
      severity          = "Critical"
    },
  )
}

resource "aws_cloudwatch_event_rule" "adg_incremental_terminated_with_errors_rule" {
  name          = "adg_incremental_terminated_with_errors_rule"
  description   = "Sends failed message to slack when adg cluster terminates with errors"
  event_pattern = <<EOF
{
  "source": [
    "aws.emr"
  ],
  "detail-type": [
    "EMR Cluster State Change"
  ],
  "detail": {
    "state": [
      "TERMINATED_WITH_ERRORS"
    ],
    "name": [
      "analytical-dataset-generator-incremental"
    ]
  }
}
EOF
}

resource "aws_cloudwatch_metric_alarm" "adg_incremental_failed_with_errors" {
  alarm_name                = "adg_incremental_failed_with_errors"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "1"
  metric_name               = "TriggeredRules"
  namespace                 = "AWS/Events"
  period                    = "60"
  statistic                 = "Sum"
  threshold                 = "1"
  alarm_description         = "This metric monitors cluster termination with errors"
  insufficient_data_actions = []
  alarm_actions             = [data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn]
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.adg_incremental_terminated_with_errors_rule.name
  }
  tags = merge(
    local.common_tags,
    {
      Name              = "adg_incremental_failed_with_errors",
      notification_type = "Error",
      severity          = "Critical"
    },
  )
}

resource "aws_cloudwatch_event_rule" "adg_incremental_success" {
  name          = "adg_incremental_success"
  description   = "checks that all steps complete"
  event_pattern = <<EOF
{
  "source": [
    "aws.emr"
  ],
  "detail-type": [
    "EMR Cluster State Change"
  ],
  "detail": {
    "state": [
      "TERMINATED"
    ],
    "name": [
      "analytical-dataset-generator-incremental"
    ],
    "stateChangeReason": [
      "{\"code\":\"ALL_STEPS_COMPLETED\",\"message\":\"Steps completed\"}"
    ]
  }
}
EOF
}


resource "aws_cloudwatch_metric_alarm" "adg_incremental_success" {
  alarm_name                = "adg_incremental_completed_all_steps"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "1"
  metric_name               = "TriggeredRules"
  namespace                 = "AWS/Events"
  period                    = "60"
  statistic                 = "Sum"
  threshold                 = "1"
  alarm_description         = "Monitoring adg incremental completion"
  insufficient_data_actions = []
  alarm_actions             = [data.terraform_remote_state.security-tools.outputs.sns_topic_london_monitoring.arn]
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.adg_incremental_success.name
  }
  tags = merge(
    local.common_tags,
    {
      Name              = "adg_incremental_success",
      notification_type = "Information",
      severity          = "Critical"
    },
  )
}
