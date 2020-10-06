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


def send_sns_message():
    payload = {}
    _sns_client = boto3.client(service_name="sns")

    publish_bucket = "${publish_bucket}"
    status_topic_arn = "${status_topic_arn}"
    adg_param_key = "analytical-dataset/adg_output/adg_params.csv"

    s3 = boto3.resource("s3")
    s3.Bucket(publish_bucket).download_file(adg_param_key, "adg_params.csv")

    with open("adg_params.csv", "r") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            payload = {"CORRELATION_ID": row[0], "S3_PREFIX": row[1]}
    json_message = json.dumps(payload)

    sns_response = _sns_client.publish(TopicArn=status_topic_arn, Message=json_message)
    the_logger.info(
        "message response", sns_response,
    )
    return sns_response


if __name__ == "__main__":
    send_sns_message()
