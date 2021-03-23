data "aws_iam_policy_document" "emr_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["elasticmapreduce.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "adg_ec2_policy" {
  statement {
    sid = "ADGEC2Actions"

    actions = [
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CancelSpotInstanceRequests",
        "ec2:Create*",
        "ec2:DeleteLaunchTemplate",
        "ec2:DeleteNetworkInterface",
        "ec2:DeleteSecurityGroup",
        "ec2:DeleteTags",
        "ec2:Describe*",
        "ec2:DetachNetworkInterface",
        "ec2:ModifyImageAttribute",
        "ec2:ModifyInstanceAttribute",
        "ec2:RequestSpotInstances",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DeleteVolume",
        "ec2:DetachVolume",
    ]

    effect = "Allow"

    resources = ["*"]
  }
}

resource "aws_iam_role" "adg_emr_service" {
  name               = "adg_emr_service"
  assume_role_policy = data.aws_iam_policy_document.emr_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "emr_attachment_full" {
  role       = aws_iam_role.adg_emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEMRFullAccessPolicy_v2"
}

resource "aws_iam_role_policy_attachment" "emr_attachment_service" {
  role       = aws_iam_role.adg_emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
}

resource "aws_iam_role_policy_attachment" "adg_ec2_policy" {
  role       = aws_iam_role.adg_emr_service.name
  policy_arn = aws_iam_policy.adg_ec2_policy.arn
}

resource "aws_iam_role_policy_attachment" "adg_emr_service_ebs_cmk" {
  role       = aws_iam_role.adg_emr_service.name
  policy_arn = aws_iam_policy.analytical_dataset_ebs_cmk_encrypt.arn
}
