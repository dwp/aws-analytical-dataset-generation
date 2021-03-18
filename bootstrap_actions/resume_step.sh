#!/bin/bash

# shellcheck source=/opt/emr/logging.sh
source /opt/emr/logging.sh

STEP_TO_START_FROM_FILE=/opt/emr/step_to_start_from.txt

function resume_from_step() {
    if [[ -f "$STEP_TO_START_FROM_FILE" ]]; then
        log_adg_message "Previous step file found"
        FAILED_STEP_NAME=`cat $STEP_TO_START_FROM_FILE`
        CURRENT_SCRIPT_NAME=`basename "$0"`
        CURRENT_STEP_NAME="${CURRENT_SCRIPT_NAME%.*}"
        log_adg_message "Current step name '$CURRENT_STEP_NAME'"

        if [[ "$FAILED_STEP_NAME" != "$CURRENT_STEP_NAME" ]]; then
            log_adg_message "Current step name '$CURRENT_STEP_NAME' doesn't match previously failed step '$FAILED_STEP_NAME', exiting"
            exit 0
        else
            log_adg_message "Current step name '$CURRENT_STEP_NAME' matches previously failed step '$FAILED_STEP_NAME', deleting file"
            rm -f "$STEP_TO_START_FROM_FILE"
        fi
    else
        log_adg_message "No previous step file found"
    fi
}

resume_from_step
