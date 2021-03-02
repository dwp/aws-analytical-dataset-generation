#!/bin/bash

source /opt/emr/logging.sh

CW_RULE=$${pdm_lambda_cw_trigger}

main() {
  log_wrapper_message ""
  put_rule
  add_lambda_permission
  put_targets
}

add_lambda_permission() {
  aws lambda add-permission \
    --function-name $${pdm_lambda_launcher_name} \
    --statement-id pdm-lambda-cw-trigger \
    --action 'lambda:InvokeFunction' \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$${aws_region}:$${aws_account_number}:rule/$CW_RULE
}

put_rule() {
  weekday=$(date +%a | tr a-z A-Z)
  day=$(date +%d)
  month=$(date +%b | tr a-z A-Z)
  year=$(date +%Y)
  aws events put-rule \
    --name $CW_RULE \
    --schedule-expression "cron(00 19 $day $month $weekday $year)"
}

put_targets() {
  aws events put-targets --rule $CW_RULE --targets --targets "Id"="1","Arn"="$${pdm_lambda_launcher_arn}"
}

log_wrapper_message() {
  log_pdm_message "$${1}" ".sh" "$$" "$${@:2}" "Running as: ,$USER"
}

main &>/var/log/adg/pdm-cw-trigger.log
