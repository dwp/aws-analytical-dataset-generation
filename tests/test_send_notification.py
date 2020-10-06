import boto3
from steps import send_notification
from moto import mock_sns

PAYLOAD = '{"CORRELATION_ID": "1", "S3_PREFIX": "aaa"}'
STATUS_TOPIC_ARN = ""
PUBLISH_BUCKET = "target"
AWS_REGION = "eu-west-2"


@mock_sns
def test_send_sns_message():
    _sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)
    _sns_client.create_topic(Name="test-", Attributes={"DisplayName": "test-topic"})
    topics_json = _sns_client.list_topics()
    topic_arn = topics_json["Topics"][0]["TopicArn"]

    # sns_resource = boto3.resource("sns", region_name=AWS_REGION)

    sns_response = _sns_client.publish(TopicArn=topic_arn, Message=PAYLOAD)

    assert (
        send_notification.send_sns_message()["ResponseMetadata"]["HTTPStatusCode"]
        == 200
    )
