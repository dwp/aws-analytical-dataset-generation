import boto3
from steps import send_notification
PAYLOAD = '{"CORRELATION_ID": "1", "S3_PREFIX": "aaa"}'
STATUS_TOPIC_ARN =
PUBLISH_BUCKET = "target"

@mock_sns
def test_send_sns_message():
    _sns_client = boto3.client(service_name="sns")
    sns_resource = boto3.resource("sns", region_name="us-east-1")

    sns_response = _sns_client.publish(TopicArn=sns_resource, Message=PAYLOAD)

    assert send_notification.send_sns_message(sns_response['ResponseMetadata']['HTTPStatusCode']==200)




