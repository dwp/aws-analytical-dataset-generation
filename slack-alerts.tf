resource "aws_cloudwatch_event_rule" "adg_cluster_termination_error_rule" {
  name          = "adg_cluster_termination_error_rule"
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
    "stateChangeReason": [
      "{\"code\":\"\"}"
    ],
    "name": [
      "analytical-dataset-generator"
    ],
    "message": [
      "Analytical-dataset-generator cluster has failed"
    ]
  }
}
EOF
}

resource "aws_cloudwatch_event_target" "adg_termination_with_errors_target" {
  rule      = aws_cloudwatch_event_rule.adg_cluster_termination_error_rule.name
  target_id = "SendFailedMsgToSlackFromADG"
  arn       = ["arn:aws:sns:eu-west-2:${lookup(local.accounts, local.environment)}:EMRStatusMetric"]
}

resource "aws_cloudwatch_event_rule" "adg_cluster_termination_success_rule" {
  name          = "adg_cluster_termination_success_rule"
  description   = "Sends success message to slack when adg cluster terminates successfully"
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
    "stateChangeReason": [
      "{\"code\":\"\"}"
    ],
    "name": [
      "analytical-dataset-generator"
    ],
    "message": [
      "Analytical-dataset-generator cluster finished successfully"
    ]
  }
}
EOF
}

resource "aws_cloudwatch_event_target" "adg_termination_successful_target" {
  rule      = aws_cloudwatch_event_rule.adg_cluster_termination_success_rule.name
  target_id = "SendSuccessMsgToSlackFromADG"
  arn       = ["arn:aws:sns:eu-west-2:${lookup(local.accounts, local.environment)}:EMRStatusMetric"]
}

