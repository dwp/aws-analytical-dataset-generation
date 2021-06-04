import boto3
from steps import send_notification
from moto import mock_sns, mock_s3

AWS_REGION = "eu-west-2"
PUBLISH_BUCKET = "target"
ADG_PARAM_KEY = "analytical-dataset/adg_output/adg_params.csv"
EXPORT_DATE = "2019-09-18"
CORRELATION_ID = "test_id"
S3_PREFIX = "test_prefix"
SNAPSHOT_TYPE_FULL = "full"

args = argparse.Namespace()
args.correlation_id = CORRELATION_ID
args.s3_prefix = S3_PREFIX
args.snapshot_type = SNAPSHOT_TYPE_FULL
args.export_date = EXPORT_DATE


@mock_sns
@mock_s3
def test_send_sns_message():
    sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)
    sns_client.create_topic(
        Name="status_topic", Attributes={"DisplayName": "test-topic"}
    )
    s3_client = boto3.client(service_name="s3")
    s3_client.create_bucket(Bucket=PUBLISH_BUCKET)
    test_data = b"CORRELATION_ID,S3_PREFIX\nabcd,analytical-dataset/2020-10-10,full,2020-01-01"
    s3_client.put_object(
        Body=test_data,
        Bucket=PUBLISH_BUCKET,
        Key=ADG_PARAM_KEY,
    )

    topics_json = sns_client.list_topics()
    status_topic_arn = topics_json["Topics"][0]["TopicArn"]

    response = send_notification.send_sns_message(
        args, PUBLISH_BUCKET, status_topic_arn, ADG_PARAM_KEY, "false", sns_client, s3_client
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_skip_sns_message():
    response = send_notification.send_sns_message(
        args, PUBLISH_BUCKET, "test-arn", ADG_PARAM_KEY, "true"
    )

    assert response is None


def test_skip_sns_message_for_incrementals():
    args.snapshot_type = "incremental"
    response = send_notification.send_sns_message(
        args, PUBLISH_BUCKET, "test-arn", ADG_PARAM_KEY, "false"
    )

    assert response is None
