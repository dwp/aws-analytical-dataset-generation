import boto3
from steps import send_notification
from moto import mock_sns, mock_s3

AWS_REGION = "eu-west-2"
PUBLISH_BUCKET = "target"
ADG_PARAM_KEY = "analytical-dataset/adg_output/adg_params.csv"


@mock_sns
@mock_s3
def test_send_sns_message():

    sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)
    sns_client.create_topic(
        Name="status_topic", Attributes={"DisplayName": "test-topic"}
    )
    s3_client = boto3.client(service_name="s3")
    s3_client.create_bucket(Bucket=PUBLISH_BUCKET)
    test_data = b"CORRELATION_ID,S3_PREFIX\nabcd,analytical-dataset/2020-10-10"
    s3_client.put_object(
        Body=test_data, Bucket=PUBLISH_BUCKET, Key=ADG_PARAM_KEY,
    )

    topics_json = sns_client.list_topics()
    status_topic_arn = topics_json["Topics"][0]["TopicArn"]

    response = send_notification.send_sns_message(
        PUBLISH_BUCKET, status_topic_arn, ADG_PARAM_KEY, sns_client, s3_client
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
