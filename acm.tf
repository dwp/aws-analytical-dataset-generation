resource "aws_acm_certificate" "analytical-dataset-generator" {
  certificate_authority_arn = data.terraform_remote_state.aws_certificate_authority.outputs.root_ca.arn
  domain_name               = "analytical-dataset-generator.${local.env_prefix[local.environment]}${local.dataworks_domain_name}"

  options {
    certificate_transparency_logging_preference = "DISABLED"
  }
}
