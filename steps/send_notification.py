import json
import boto3
import csv
import os
import sys
import argparse

from datetime import datetime, timedelta
from steps.logger import setup_logging
from steps.resume_step import should_skip_step

ARG_SNAPSHOT_TYPE = "snapshot_type"
ARG_S3_PREFIX = "s3_prefix"
ARG_CORRELATION_ID = "correlation_id"
ARG_EXPORT_DATE = "export_date"
SNAPSHOT_TYPE_INCREMENTAL = "incremental"
SNAPSHOT_TYPE_FULL = "full"
ARG_SNAPSHOT_TYPE_VALID_VALUES = [SNAPSHOT_TYPE_FULL, SNAPSHOT_TYPE_INCREMENTAL]

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def send_sns_message(
    args, publish_bucket, status_topic_arn, adg_param_key, skip_message_sending, sns_client=None, s3_client=None
):
    if exit_if_skipping_step(skip_message_sending, args.snapshot_type):
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
            payload = {"correlation_id": row[0], "s3_prefix": row[1], "snapshot_type": row[2], "export_date": row[3]}
    json_message = json.dumps(payload)

    sns_response = sns_client.publish(TopicArn=status_topic_arn, Message=json_message)
    the_logger.info(
        "message response", sns_response,
    )
    return sns_response


def get_parameters():
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job"
    )

    parser.add_argument("--correlation_id", default="0")
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    parser.add_argument("--snapshot_type", default="full")
    parser.add_argument("--export_date", default=datetime.now().strftime("%Y-%m-%d"))
    args, unrecognized_args = parser.parse_known_args()
    the_logger.warning(
        "Unrecognized args %s found for the correlation id %s",
        unrecognized_args,
        args.correlation_id,
    )
    validate_required_args(args)

    return args


def validate_required_args(args):
    required_args = [ARG_CORRELATION_ID, ARG_S3_PREFIX, ARG_SNAPSHOT_TYPE, ARG_EXPORT_DATE]
    missing_args = []
    for required_message_key in required_args:
        if required_message_key not in args:
            missing_args.append(required_message_key)
    if missing_args:
        raise argparse.ArgumentError(
            None,
            "ArgumentError: The following required arguments are missing: {}".format(
                ", ".join(missing_args)
            ),
        )
    if args.snapshot_type.lower() not in ARG_SNAPSHOT_TYPE_VALID_VALUES:
        raise argparse.ArgumentError(
            None,
            "ArgumentError: Valid values for snapshot_type are: {}".format(
                ", ".join(ARG_SNAPSHOT_TYPE_VALID_VALUES)
            ),
        )


def exit_if_skipping_step(skip_message_sending, snapshot_type):
    if skip_message_sending.lower() == "true":
        the_logger.info(
            f"Skipping SNS message sending due to skip_message_sending value of {skip_message_sending}",
        )
        return True

    if snapshot_type.lower() == SNAPSHOT_TYPE_INCREMENTAL.lower():
        the_logger.info(
            f"Skipping SNS message sending due to snapshot_type value of {snapshot_type}",
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
    args = get_parameters()
    send_sns_message(args, publish_bucket, status_topic_arn, adg_param_key, skip_message_sending)
