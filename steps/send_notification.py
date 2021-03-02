import json
import boto3
import csv
import os
import sys

from steps.logger import setup_logging
from steps.resume_step import should_skip_step

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def send_sns_message(
    publish_bucket, status_topic_arn, adg_param_key, skip_message_sending, sns_client=None, s3_client=None
):
    if exit_if_skipping_step(skip_message_sending):
        return None

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


def exit_if_skipping_step(skip_message_sending):
    if skip_message_sending.lower() == "true":
        the_logger.info(
            f"Skipping SNS message sending due to skip_message_sending value of {skip_message_sending}",
        )
        return True

    if should_skip_step(the_logger, "submit-job"):
        the_logger.info(
            "Step needs to be skipped so will exit without error"
        )
        return True
    

    return False


if __name__ == "__main__":
    publish_bucket = "${publish_bucket}"
    status_topic_arn = "${status_topic_arn}"
    skip_message_sending = "${skip_message_sending}"
    adg_param_key = "analytical-dataset/full/adg_output/adg_params.csv"
    send_sns_message(publish_bucket, status_topic_arn, adg_param_key, skip_message_sending)
