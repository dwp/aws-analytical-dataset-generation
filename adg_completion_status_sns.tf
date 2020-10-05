resource "aws_sns_topic" "adg_completion_status_sns" {
  name = "adg_completion_status_sns"

  tags = merge(
    local.common_tags,
    {
      "Name" = "adg_completion_status_sns"
    },
  )
}

output "adg_completion_status_sns_topic" {
  value = aws_sns_topic.adg_completion_status_sns
}
