resource "aws_cloudwatch_log_metric_filter" "all_collections" {
  name           = "AllCollectionsProcessingTimeFilter"
  pattern        = "[..., all=\"all\", collections=\"collections:\", time, apostrophe, bracket]"
  log_group_name = aws_cloudwatch_log_group.adg_cw_steps_loggroup.name

  metric_transformation {
    name          = "AllCollectionsProcessingTime"
    namespace     = "EMR/Collections"
    value         = "$time"
    default_value = "0"
  }
}
