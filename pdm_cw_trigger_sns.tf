resource "aws_sns_topic" "pdm_cw_trigger_sns" {
  name = "pdm_cw_trigger_sns"

  tags = merge(
    local.common_tags,
    {
      "Name" = "pdm_cw_trigger_sns"
    },
  )
}

output "pdm_cw_trigger_sns_topic" {
  value = aws_sns_topic.pdm_cw_trigger_sns
}
