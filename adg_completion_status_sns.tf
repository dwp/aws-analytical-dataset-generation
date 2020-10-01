resource "aws_sns_topic" "adg_completion_status_sns" {
  name = "adg_completion_status_sns"

  tags = merge(
    local.common_tags,
    {
      "Name" = "adg_completion_status_sns"
    },
  )
}

resource "aws_sns_topic_policy" "adg_completion_status_sns" {
  arn    = aws_sns_topic.adg_completion_status_sns.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

data "aws_iam_policy_document" "sns_topic_policy" {
  policy_id = "AdgCompletionStatusSnsTopicPolicy"

  statement {
    sid = "AdgSnsPolicy"

    actions = [
      "SNS:Get*",
      "SNS:List*",
      "SNS:Subscribe",
      "SNS:Publish",
      "SNS:AddPermission",
      "SNS:RemovePermission",
      "SNS:Receive",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"

      values = [
        local.account[local.environment],
      ]
    }

    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
      "*"]
    }

    resources = [
      aws_sns_topic.adg_completion_status_sns.arn,
    ]
  }
}

output "adg_completion_status_sns_topic" {
  value = aws_sns_topic.adg_completion_status_sns
}
