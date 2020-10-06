import json
import boto3
import csv
import os

from steps.logger import setup_logging

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def send_sns_message(
    publish_bucket, status_topic_arn, adg_param_key, sns_client=None, s3_client=None
):
    payload = {}
    csv_name = "adg_params.csv"
    if not sns_client:
        sns_client = boto3.client(service_name="sns")
    if not s3_client:
        s3_client = boto3.client(service_name="s3")

    with open(csv_name, "wb") as data:
        s3_client.download_fileobj(
            Bucket=publish_bucket, Key=adg_param_key, Fileobj=data
        )

    with open(csv_name, "r") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            payload = {"correlation_id": row[0], "s3_prefix": row[1]}
    json_message = json.dumps(payload)

    sns_response = sns_client.publish(TopicArn=status_topic_arn, Message=json_message)
    the_logger.info(
        "message response", sns_response,
    )
    return sns_response


if __name__ == "__main__":
    publish_bucket = "${publish_bucket}"
    status_topic_arn = "${status_topic_arn}"
    adg_param_key = "analytical-dataset/adg_output/adg_params.csv"
    send_sns_message(publish_bucket, status_topic_arn, adg_param_key)
