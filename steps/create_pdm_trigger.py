import boto3
import os

from datetime import datetime, timedelta
from steps.logger import setup_logging
from steps.resume_step import should_skip_step

the_logger = setup_logging(
    log_level=os.environ["ADG_LOG_LEVEL"].upper()
    if "ADG_LOG_LEVEL" in os.environ
    else "INFO",
    log_path="${log_path}",
)


def create_pdm_trigger(
    publish_bucket, status_topic_arn, adg_param_key, skip_message_sending, sns_client=None, s3_client=None
):
    if exit_if_skipping_step(skip_message_sending):
        return None

    client = get_events_client()
    now = datetime.now()
    do_not_run_before = now.replace(hour=15, minute=00, second=00)
    cron = get_cron(now, do_not_run_before)

    rule_name = put_cloudwatch_event_rule(client, now, cron)
    put_cloudwatch_event_target(client, now, rule_name)


def get_events_client():
    return boto3.client("events")


def put_cloudwatch_event_rule(client, now, cron):
    now_string = now.strftime("%d_%m_%Y_%H_%M_%S")
    name = f"pdm_cw_emr_launcher_schedule_{now_string}"

    the_logger.info(
        f"Putting new cloudwatch event rule with name of '{name}' and cron of '{cron}'",
    )

    response = client.put_rule(
        Name=name,
        ScheduleExpression=cron,
        State="ENABLED",
        Description='Triggers PDM EMR Launcher',
    )

    the_logger.info(
        f"Put new cloudwatch event rule",
    )

    return name


def put_cloudwatch_event_target(client, now, rule_name):
    now_string = now.strftime("%d_%m_%Y_%H_%M_%S")
    id_string = f"pdm_cw_emr_launcher_target_{now_string}"

    the_logger.info(
        f"Putting new cloudwatch event target with id of '{id_string}'",
    )

    response = client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': id_string,
                'Arn': "${pdm_lambda_trigger_arn}",
            },
        ]
    )

    the_logger.info(
        f"Put new cloudwatch event target",
    )


def should_step_be_skipped(now, do_not_trigger_after):
    if now > do_not_trigger_after:
        the_logger.info(
            f"Skipping PDM triggering as datetime now '{now}' if after cut off of '{do_not_trigger_after}'",
        )
        return True

    if should_skip_step(the_logger, "trigger-pdm"):
        the_logger.info(
            "Step needs to be skipped so will exit without error"
        )
        return True
    

    return False


def get_cron(now, do_not_run_before):
    if now < do_not_run_before:
        cron = f'{do_not_run_before.strftime("%M")} {do_not_run_before.strftime("%H")} {do_not_run_before.strftime("%d")} {do_not_run_before.strftime("%m")} ? {do_not_run_before.strftime("%y")}'
        the_logger.info(
            "Time now is before cut off time so returning cut off time cron", cron,
        )
        return cron
    
    ten_minutes_from_now = now + timedelta(minutes = 5)
    cron = f'{ten_minutes_from_now.strftime("%M")} {ten_minutes_from_now.strftime("%H")} {ten_minutes_from_now.strftime("%d")} {ten_minutes_from_now.strftime("%m")} ? {ten_minutes_from_now.strftime("%y")}'
    the_logger.info(
        "Time now is after cut off time so returning cron for 5 minutes time", cron,
    )
    return cron



if __name__ == "__main__":
    publish_bucket = "${publish_bucket}"
    status_topic_arn = "${status_topic_arn}"
    skip_message_sending = "${skip_message_sending}"
    adg_param_key = "analytical-dataset/full/adg_output/adg_params.csv"
    send_sns_message(publish_bucket, status_topic_arn, adg_param_key, skip_message_sending)
