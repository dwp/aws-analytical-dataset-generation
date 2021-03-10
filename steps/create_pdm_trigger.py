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

EXPORT_DATE_FILE_NAME = "/opt/emr/export_date.txt"


def create_pdm_trigger(
    skip_pdm_trigger,
    events_client=None
):
    now = get_now()
    do_not_run_after = generate_cut_off_date(EXPORT_DATE_FILE_NAME)

    if should_step_be_skipped(skip_pdm_trigger, now, do_not_run_after):
        return None

    if events_client is None:
        events_client = get_events_client()

    do_not_run_before = generate_do_not_run_before_date(EXPORT_DATE_FILE_NAME)
    cron = get_cron(now, do_not_run_before)

    rule_name = put_cloudwatch_event_rule(client, now, cron)
    put_cloudwatch_event_target(client, now, rule_name)


def get_now():
    return datetime.now()


def generate_cut_off_date(export_date_file):
    if not os.path.isfile(export_date_file):
        return None

    with open(export_date_file, "r") as f:
        export_date = f.readlines().split()

    if not export_date:
        return None

    export_date_parsed = datetime.strptime(date_time_str, '%Y-%m-%d')
    day_after_export_date = now + timedelta(days = 1)

    return day_after_export_date.replace(hour=3, minute=00, second=00)


def generate_do_not_run_before_date(export_date_file):
    if not os.path.isfile(export_date_file):
        return None

    with open(export_date_file, "r") as f:
        export_date = f.readlines().split()

    if not export_date:
        return None

    export_date_parsed = datetime.strptime(date_time_str, '%Y-%m-%d')
    return export_date_parsed.replace(hour=15, minute=00, second=00)


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


def check_should_skip_step():
    return should_skip_step(the_logger, "trigger-pdm")


def should_step_be_skipped(skip_pdm_trigger, now, do_not_trigger_after):
    if skip_pdm_trigger.lower() == "true":
        the_logger.info(
            f"Skipping PDM trigger due to skip_pdm_trigger value of {skip_pdm_trigger}",
        )
        return True

    if now > do_not_trigger_after:
        the_logger.info(
            f"Skipping PDM triggering as datetime now '{now}' if after cut off of '{do_not_trigger_after}'",
        )
        return True

    if check_should_skip_step():
        the_logger.info(
            "Step needs to be skipped so will exit without error"
        )
        return True
    

    return False


def get_cron(now, do_not_run_before):
    if now < do_not_run_before:
        cron = f'{do_not_run_before.strftime("%M")} {do_not_run_before.strftime("%H")} {do_not_run_before.strftime("%d")} {do_not_run_before.strftime("%m")} ? {do_not_run_before.year}'
        the_logger.info(
            "Time now is before cut off time so returning cut off time cron", cron,
        )
        return cron
    
    ten_minutes_from_now = now + timedelta(minutes = 5)
    cron = f'{ten_minutes_from_now.strftime("%M")} {ten_minutes_from_now.strftime("%H")} {ten_minutes_from_now.strftime("%d")} {ten_minutes_from_now.strftime("%m")} ? {ten_minutes_from_now.year}'
    the_logger.info(
        "Time now is after cut off time so returning cron for 5 minutes time", cron,
    )
    return cron



if __name__ == "__main__":
    skip_pdm_trigger = "${skip_pdm_trigger}"
    send_sns_message(skip_pdm_trigger)
