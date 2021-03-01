#!/bin/bash

source /opt/emr/logging.sh

STEP_TO_START_FROM_FILE=/opt/emr/step_to_start_from.txt

function resume_from_step() {
    if [[ -f $STEP_TO_START_FROM_FILE ]]; then
        log_adg_message "Previous step file found"
        STEP=`cat $STEP_TO_START_FROM_FILE`
        CURRENT_FILE_NAME=`basename "$0"`
        FILE_NAME_NO_EXT="${CURRENT_FILE_NAME%.*}"
        log_adg_message "Current file name $FILE_NAME_NO_EXT"

        if [[ $STEP != $FILE_NAME_NO_EXT ]]; then
            log_adg_message "Current step name $FILE_NAME_NO_EXT doesn't match previously failed step $STEP, exiting"
            exit 0
        else
            log_adg_message "Current step name $FILE_NAME_NO_EXT matches previously failed step $STEP, deleting file"
            rm -f $STEP_TO_START_FROM_FILE
        fi
    else
        log_adg_message "No previous step file found"
    fi
}

resume_from_step
