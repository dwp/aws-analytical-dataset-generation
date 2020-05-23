resource "aws_acm_certificate" "analytical-dataset-generator" {
  certificate_authority_arn = data.terraform_remote_state.aws_certificate_authority.outputs.root_ca.arn
  domain_name               = "analytical-dataset-generator.${local.env_prefix[local.environment]}${local.dataworks_domain_name}"

  options {
    certificate_transparency_logging_preference = "DISABLED"
  }
}

data "aws_iam_policy_document" "analytical_dataset_acm" {
  statement {
    effect = "Allow"

    actions = [
      "acm:ExportCertificate",
    ]

    resources = [
      aws_acm_certificate.analytical-dataset-generator.arn
    ]
  }
}

resource "aws_iam_policy" "analytical_dataset_acm" {
  name        = "ACMExportDatasetGeneratorCert"
  description = "Allow export of Dataset Generator certificate"
  policy      = data.aws_iam_policy_document.analytical_dataset_acm.json
}
