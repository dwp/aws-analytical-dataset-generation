import boto3
import unittest

from steps import trigger_pdm
from datetime import datetime


# @mock_events
# def test_send_sns_message():
#     sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)
#     sns_client.create_topic(
#         Name="status_topic", Attributes={"DisplayName": "test-topic"}
#     )
#     s3_client = boto3.client(service_name="s3")
#     s3_client.create_bucket(Bucket=PUBLISH_BUCKET)
#     test_data = b"CORRELATION_ID,S3_PREFIX\nabcd,analytical-dataset/2020-10-10"
#     s3_client.put_object(
#         Body=test_data,
#         Bucket=PUBLISH_BUCKET,
#         Key=ADG_PARAM_KEY,
#     )

#     topics_json = sns_client.list_topics()
#     status_topic_arn = topics_json["Topics"][0]["TopicArn"]

#     response = send_notification.send_sns_message(
#         PUBLISH_BUCKET, status_topic_arn, ADG_PARAM_KEY, "false", sns_client, s3_client
#     )

#     assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_put_cloudwatch_event_rule():
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    cron = "1 1 1 1 1 1 1"
    
    events_client = mock.MagicMock()
    events_client.put_rule = mock.MagicMock()

    expected = "pdm_cw_emr_launcher_schedule_18_09_19_23_57_19"
    actual = send_notification.put_cloudwatch_event_rule(
        events_client, now, cron
    )

    events_client.put_rule.assert_called_once_with(
        Name=expected,
        ScheduleExpression=cron,
        State="ENABLED",
        Description='Triggers PDM EMR Launcher',
    )

    assert actual == expected


def test_put_cloudwatch_event_target():
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    id_string = "pdm_cw_emr_launcher_target_18_09_19_23_57_19"
    rule_name = "pdm_cw_emr_launcher_schedule_18_09_19_23_57_19"

    events_client = mock.MagicMock()
    events_client.put_targets = mock.MagicMock()

    actual = send_notification.put_cloudwatch_event_target(
        events_client, now, cron
    )

    events_client.put_targets.assert_called_once_with(
        Rule=rule_name,
        Targets=[
            {
                'Id': id_string,
                'Arn': "${pdm_lambda_trigger_arn}",
            },
        ]
    )


def test_should_skip_returns_true_when_after_cut_off(monkeypatch):
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    do_not_trigger_after = datetime.strptime("18/09/19 22:55:19", '%d/%m/%y %H:%M:%S')

    monkeypatch.setattr(
        steps.resume_step, "should_skip_step", False
    )

    actual = trigger_pdm.should_step_be_skipped(
        now, 
        do_not_trigger_after
    )

    assert True == actual


def test_should_skip_returns_true_when_after_cut_off_but_resume_step_returns_true(monkeypatch):
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

    monkeypatch.setattr(
        steps.resume_step, "should_skip_step", True
    )

    actual = trigger_pdm.should_step_be_skipped(
        now, 
        do_not_trigger_after
    )

    assert True == actual


def test_should_skip_returns_false_when_before_cut_off_and_resume_step_returns_false(monkeypatch):
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

    monkeypatch.setattr(
        steps.resume_step, "should_skip_step", False
    )

    actual = trigger_pdm.should_step_be_skipped(
        now, 
        do_not_trigger_after
    )

    assert False == actual


def test_get_cron_gives_cut_out_time_when_before_cut_off():
    now = datetime.strptime("18/09/19 01:55:19", '%d/%m/%y %H:%M:%S')
    do_not_run_before = datetime.strptime("18/09/19 02:55:19", '%d/%m/%y %H:%M:%S')

    expected = "19 55 02 18 09 ? 19"
    actual = trigger_pdm.get_cron(
        now, 
        do_not_run_before
    )

    assert expected == actual


def test_get_cron_gives_now_plus_5_minutes_when_after_cut_off():
    now = datetime.strptime("18/09/19 01:57:19", '%d/%m/%y %H:%M:%S')
    do_not_run_before = datetime.strptime("18/09/19 00:55:19", '%d/%m/%y %H:%M:%S')

    expected = "19 02 02 18 09 ? 19"
    actual = trigger_pdm.get_cron(
        now, 
        do_not_run_before
    )

    assert expected == actual


def test_get_cron_gives_cut_out_time_when_before_cut_off_over_date_boundary():
    now = datetime.strptime("18/09/19 23:55:19", '%d/%m/%y %H:%M:%S')
    do_not_run_before = datetime.strptime("19/09/19 01:55:19", '%d/%m/%y %H:%M:%S')

    expected = "19 55 01 19 09 ? 19"
    actual = trigger_pdm.get_cron(
        now, 
        do_not_run_before
    )

    assert expected == actual


def test_get_cron_gives_now_plus_5_minutes_when_after_cut_off_over_date_boundary():
    now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
    do_not_run_before = datetime.strptime("18/09/19 22:55:19", '%d/%m/%y %H:%M:%S')

    expected = "19 02 00 19 09 ? 19"
    actual = trigger_pdm.get_cron(
        now, 
        do_not_run_before
    )

    assert expected == actual
