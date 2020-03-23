import requests
import pysecret
import boto3
import os

from pysecret.aws import AWSSecret


def get_boto_session():
    session = None
    profile = os.environ.get("AWS_DEFAULT_PROFILE")
    role = os.environ.get("AWS_ASSUME_ROLE")
    if role:
        account = os.environ.get("AWS_ACCOUNT")
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=f"arn:aws:iam::{account}:role/{role}", RoleSessionName="GetSecret"
        )
        session = boto3.session.Session(
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
        )
    else:
        session = boto3.session.Session(profile_name=profile)
    return session._session


session = get_boto_session()
secret = AWSSecret(botocore_session=session)

CONFIG_S3_BUCKET = secret.get_secret_value(
    secret_id="ADG-Payload", key="ADG_S3_CONFIG_BUCKET"
)


def lambda_handler(event, context):
    url = "https://internal-emr-cluster-broker-lb-1976331568.eu-west-2.elb.amazonaws.com/cluster/submit"
    headers = {"Content-Type: application/json"}
    files = {
        "file": open(
            "{CONFIG_S3_BUCKET}/component/analytical-dataset-generation/analytical-dataset-generator-cluster-payload.json"
        )
    }

    response = requests.post(url, headers, files=files)
    print(response.text)  # TEXT/HTML
