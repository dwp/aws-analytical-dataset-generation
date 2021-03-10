import boto3
import unittest
import os
import pytest

from steps import create_pdm_trigger
from datetime import datetime
from unittest import mock


class TestReplayer(unittest.TestCase):
    @mock.patch("steps.create_pdm_trigger.put_cloudwatch_event_target")
    @mock.patch("steps.create_pdm_trigger.put_cloudwatch_event_rule")
    @mock.patch("steps.create_pdm_trigger.get_cron")
    @mock.patch("steps.create_pdm_trigger.generate_do_not_run_before_date")
    @mock.patch("steps.create_pdm_trigger.get_events_client")
    @mock.patch("steps.create_pdm_trigger.should_step_be_skipped")
    @mock.patch("steps.create_pdm_trigger.generate_cut_off_date")
    @mock.patch("steps.create_pdm_trigger.get_now")
    def test_create_pdm_trigger(
        self,
        get_now_mock,
        generate_cut_off_date_mock,
        should_step_be_skipped_mock,
        get_events_client_mock,
        generate_do_not_run_before_date_mock,
        get_cron_mock,
        put_cloudwatch_event_rule_mock,
        put_cloudwatch_event_target_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_run_after = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_run_before = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        cron = "test cron"
        rule_name = "test rule"

        events_client = mock.MagicMock()
        get_now_mock = mock.MagicMock()
        generate_cut_off_date_mock = mock.MagicMock()
        should_step_be_skipped_mock = mock.MagicMock()
        get_events_client_mock = mock.MagicMock()
        generate_do_not_run_before_date_mock = mock.MagicMock()
        get_cron_mock = mock.MagicMock()
        put_cloudwatch_event_rule_mock = mock.MagicMock()
        put_cloudwatch_event_target_mock = mock.MagicMock()

        get_now_mock.return_value = now
        generate_cut_off_date_mock.return_value = do_not_run_after
        should_step_be_skipped_mock.return_value = False
        get_events_client_mock.return_value = events_client
        generate_do_not_run_before_date_mock.return_value = do_not_run_before
        get_cron_mock.return_value = cron
        put_cloudwatch_event_rule_mock.return_value = rule_name
        
        response = create_pdm_trigger.create_pdm_trigger(
            False, 
        )
        
        get_now_mock.assert_called_once()
        generate_cut_off_date_mock.assert_called_once()
        should_step_be_skipped_mock.assert_called_once_with(
            "false",
            now,
            do_not_run_after,
        )
        get_events_client_mock.assert_called_once()
        generate_do_not_run_before_date_mock.assert_called_once()
        get_cron_mock.assert_called_once_with(
            now,
            do_not_run_before,
        )
        put_cloudwatch_event_rule_mock.assert_called_once_with(
            events_client,
            now,
            cron,
        )
        put_cloudwatch_event_target_mock.assert_called_once_with(
            events_client,
            now,
            rule_name,
        )


    def test_generate_do_not_run_before_date(self):
        export_date = "2020-10-20"
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        with open(export_date_file, "wt") as f:
            export_date = f.write(export_date)

        expected = datetime.strptime("20/10/2020 15:00:00", '%d/%m/%Y %H:%M:%S')
        actual = create_pdm_trigger.generate_do_not_run_before_date(export_date_file)

        assert actual == expected


    def test_generate_do_not_run_before_date_when_no_file(self):
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        expected = None
        actual = create_pdm_trigger.generate_do_not_run_before_date(export_date_file)

        assert actual == expected


    def test_generate_do_not_run_before_date_when_empty_file(self):
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        with open(export_date_file, "wt") as f:
            export_date = f.write("")

        expected = None
        actual = create_pdm_trigger.generate_do_not_run_before_date(export_date_file)

        assert actual == expected


    def test_generate_cut_off_date(self):
        export_date = "2020-10-20"
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        with open(export_date_file, "wt") as f:
            export_date = f.write(export_date)

        expected = datetime.strptime("21/10/2020 03:00:00", '%d/%m/%Y %H:%M:%S')
        actual = create_pdm_trigger.generate_cut_off_date(export_date_file)

        assert actual == expected


    def test_generate_cut_off_date_when_no_file(self):
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        expected = None
        actual = create_pdm_trigger.generate_cut_off_date(export_date_file)

        assert actual == expected


    def test_generate_cut_off_date_when_empty_file(self):
        export_date_file = "/tmp/test.txt"
        if os.path.isfile(export_date_file):
            os.remove(export_date_file)

        with open(export_date_file, "wt") as f:
            export_date = f.write("")

        expected = None
        actual = create_pdm_trigger.generate_cut_off_date(export_date_file)

        assert actual == expected


    def test_put_cloudwatch_event_rule(self):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        cron = "1 1 1 1 1 1 1"
        
        events_client = mock.MagicMock()
        events_client.put_rule = mock.MagicMock()

        expected = "pdm_cw_emr_launcher_schedule_18_09_2019_23_57_19"
        actual = create_pdm_trigger.put_cloudwatch_event_rule(
            events_client, now, cron
        )

        events_client.put_rule.assert_called_once_with(
            Name=expected,
            ScheduleExpression=cron,
            State="ENABLED",
            Description='Triggers PDM EMR Launcher',
        )

        assert actual == expected


    def test_put_cloudwatch_event_target(self):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        id_string = "pdm_cw_emr_launcher_target_18_09_2019_23_57_19"
        rule_name = "pdm_cw_emr_launcher_schedule_18_09_2019_23_57_19"

        events_client = mock.MagicMock()
        events_client.put_targets = mock.MagicMock()

        actual = create_pdm_trigger.put_cloudwatch_event_target(
            events_client, now, rule_name
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


    @mock.patch("steps.create_pdm_trigger.check_should_skip_step")
    def test_should_skip_returns_true_when_after_cut_off(
        self,
        check_should_skip_step_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_trigger_after = datetime.strptime("18/09/19 22:55:19", '%d/%m/%y %H:%M:%S')

        check_should_skip_step_mock = mock.MagicMock()
        check_should_skip_step_mock.return_value = False

        actual = create_pdm_trigger.should_step_be_skipped(
            "false",
            now, 
            do_not_trigger_after
        )

        assert True == actual


    @mock.patch("steps.create_pdm_trigger.check_should_skip_step")
    def test_should_skip_returns_true_when_after_cut_off_but_resume_step_returns_true(
        self,
        check_should_skip_step_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

        check_should_skip_step_mock = mock.MagicMock()
        check_should_skip_step_mock.return_value = True

        actual = create_pdm_trigger.should_step_be_skipped(
            "false",
            now, 
            do_not_trigger_after
        )

        assert True == actual


    @mock.patch("steps.create_pdm_trigger.check_should_skip_step")
    def test_should_skip_returns_true_when_skip_setting_set_to_true(
        self,
        check_should_skip_step_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

        check_should_skip_step_mock = mock.MagicMock()
        check_should_skip_step_mock.return_value = False

        actual = create_pdm_trigger.should_step_be_skipped(
            "true",
            now, 
            do_not_trigger_after
        )

        assert True == actual


    @mock.patch("steps.create_pdm_trigger.check_should_skip_step")
    def test_should_skip_returns_true_when_skip_setting_set_to_true_upper_case(
        self,
        check_should_skip_step_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

        check_should_skip_step_mock = mock.MagicMock()
        check_should_skip_step_mock.return_value = False

        actual = create_pdm_trigger.should_step_be_skipped(
            "TRUE",
            now, 
            do_not_trigger_after
        )

        assert True == actual


    @mock.patch("steps.create_pdm_trigger.check_should_skip_step")
    def test_should_skip_returns_false_when_before_cut_off_and_resume_step_returns_false(
        self,
        check_should_skip_step_mock,
    ):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_trigger_after = datetime.strptime("18/09/19 23:59:19", '%d/%m/%y %H:%M:%S')

        check_should_skip_step_mock = mock.MagicMock()
        check_should_skip_step_mock.return_value = False

        actual = create_pdm_trigger.should_step_be_skipped(
            "false",
            now, 
            do_not_trigger_after
        )

        assert False == actual


    def test_get_cron_gives_cut_out_time_when_before_cut_off(self):
        now = datetime.strptime("18/09/19 01:55:19", '%d/%m/%y %H:%M:%S')
        do_not_run_before = datetime.strptime("18/09/19 02:55:19", '%d/%m/%y %H:%M:%S')

        expected = "55 02 18 09 ? 2019"
        actual = create_pdm_trigger.get_cron(
            now, 
            do_not_run_before
        )

        assert expected == actual


    def test_get_cron_gives_now_plus_5_minutes_when_after_cut_off(self):
        now = datetime.strptime("18/09/19 01:57:19", '%d/%m/%y %H:%M:%S')
        do_not_run_before = datetime.strptime("18/09/19 00:55:19", '%d/%m/%y %H:%M:%S')

        expected = "02 02 18 09 ? 2019"
        actual = create_pdm_trigger.get_cron(
            now, 
            do_not_run_before
        )

        assert expected == actual


    def test_get_cron_gives_cut_out_time_when_before_cut_off_over_date_boundary(self):
        now = datetime.strptime("18/09/19 23:55:19", '%d/%m/%y %H:%M:%S')
        do_not_run_before = datetime.strptime("19/09/19 01:55:19", '%d/%m/%y %H:%M:%S')

        expected = "55 01 19 09 ? 2019"
        actual = create_pdm_trigger.get_cron(
            now, 
            do_not_run_before
        )

        assert expected == actual


    def test_get_cron_gives_now_plus_5_minutes_when_after_cut_off_over_date_boundary(self):
        now = datetime.strptime("18/09/19 23:57:19", '%d/%m/%y %H:%M:%S')
        do_not_run_before = datetime.strptime("18/09/19 22:55:19", '%d/%m/%y %H:%M:%S')

        expected = "02 00 19 09 ? 2019"
        actual = create_pdm_trigger.get_cron(
            now, 
            do_not_run_before
        )

        assert expected == actual


if __name__ == "__main__":
    unittest.main()
