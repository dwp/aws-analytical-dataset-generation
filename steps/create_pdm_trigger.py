import boto3
import argparse
import os
import json

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


def create_pdm_trigger(
    args,
    skip_pdm_trigger,
    events_client=None
):
    now = get_now()
    do_not_run_after = generate_cut_off_date(args.export_date, args.pdm_start_do_not_run_after_hour)

    if should_step_be_skipped(skip_pdm_trigger, now, do_not_run_after):
        return None

    if events_client is None:
        events_client = get_events_client()

    do_not_run_before = generate_do_not_run_before_date(args.export_date, args.pdm_start_do_not_run_before_hour)
    cron = get_cron(now, do_not_run_before)

    rule_name = put_cloudwatch_event_rule(events_client, now, cron)
    put_cloudwatch_event_target(
        events_client, 
        now, 
        rule_name, 
        args.export_date, 
        args.correlation_id,
        args.snapshot_type,
        args.s3_prefix,
    )


def get_parameters():
    parser = argparse.ArgumentParser(
        description="Receive args provided to spark submit job"
    )

    parser.add_argument("--correlation_id", default="0")
    parser.add_argument("--s3_prefix", default="${s3_prefix}")
    parser.add_argument("--snapshot_type", default="full")
    parser.add_argument("--export_date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--pdm_start_do_not_run_after_hour", default=int("${pdm_start_do_not_run_after_hour}"))
    parser.add_argument("--pdm_start_do_not_run_before_hour", default=int("${pdm_start_do_not_run_before_hour}"))
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


def get_now():
    return datetime.utcnow()


def generate_cut_off_date(export_date, do_not_run_after_hour):
    export_date_parsed = datetime.strptime(export_date, '%Y-%m-%d')
    day_after_export_date = export_date_parsed + timedelta(days = 1)
    return day_after_export_date.replace(hour=do_not_run_after_hour, minute=00, second=00)


def generate_do_not_run_before_date(export_date, do_not_run_before_hour):
    export_date_parsed = datetime.strptime(export_date, '%Y-%m-%d')
    return export_date_parsed.replace(hour=do_not_run_before_hour, minute=00, second=00)


def get_events_client():
    return boto3.client("events")


def put_cloudwatch_event_rule(client, now, cron):
    now_string = now.strftime("%d_%m_%Y_%H_%M_%S")
    name = f"pdm_cw_emr_launcher_schedule_{now_string}"

    the_logger.info(
        f"Putting new cloudwatch event rule with name of '{name}' and cron of '{cron}'",
    )

    client.put_rule(
        Name=name,
        ScheduleExpression=f"cron({cron})",
        State="ENABLED",
        Description='Triggers PDM EMR Launcher',
    )

    the_logger.info(
        f"Put new cloudwatch event rule",
    )

    return name


def put_cloudwatch_event_target(
        client, 
        now, 
        rule_name, 
        export_date,
        correlation_id,
        snapshot_type,
        s3_prefix,
    ):
    now_string = now.strftime("%d_%m_%Y_%H_%M_%S")
    id_string = f"pdm_cw_emr_launcher_target_{now_string}"

    the_logger.info(
        f"Putting new cloudwatch event target with id of '{id_string}'",
    )

    input_dumped = json.dumps({
        'export_date': export_date,
        'correlation_id': correlation_id,
        'snapshot_type': snapshot_type,
        's3_prefix': s3_prefix
    })

    client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': id_string,
                'Arn': "${pdm_lambda_trigger_arn}",
                'Input': f"{input_dumped}"
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
        five_minutes_from_do_not_run_before = do_not_run_before + timedelta(minutes = 5)
        cron = f'{five_minutes_from_do_not_run_before.strftime("%M")} {five_minutes_from_do_not_run_before.strftime("%H")} {five_minutes_from_do_not_run_before.strftime("%d")} {five_minutes_from_do_not_run_before.strftime("%m")} ? {five_minutes_from_do_not_run_before.year}'
        the_logger.info(
            f"Time now is before cut off time so returning cut off time cron of '{cron}' for 5 minutes after the cut off",
        )
        return cron
    
    five_minutes_from_now = now + timedelta(minutes = 5)
    cron = f'{five_minutes_from_now.strftime("%M")} {five_minutes_from_now.strftime("%H")} {five_minutes_from_now.strftime("%d")} {five_minutes_from_now.strftime("%m")} ? {five_minutes_from_now.year}'
    the_logger.info(
        f"Time now is after cut off time so returning cron of '{cron}' for 5 minutes time",
    )
    return cron



if __name__ == "__main__":
    args = get_parameters()
    skip_pdm_trigger = "${skip_pdm_trigger}"
    create_pdm_trigger(args, skip_pdm_trigger)
