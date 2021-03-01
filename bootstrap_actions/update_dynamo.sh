#!/bin/bash
(
    INSTANCE_ROLE=$(jq .instanceRole /mnt/var/lib/info/extraInstanceData.json)

    #only log on master to avoid duplication
    if [[ "$INSTANCE_ROLE" != '"MASTER"' ]]; then
      exit 0
    fi
    source /opt/emr/logging.sh

    function log_wrapper_message() {
        log_adg_message "$${1}" "update_dynamo.sh" "$${PID}" "$${@:2}" "Running as: ,$USER"
    }

  log_wrapper_message "Start running update_dynamo.sh Shell"

  STEP_DETAILS_DIR=/mnt/var/lib/info/steps
  CORRELATION_ID_FILE=/opt/emr/correlation_id.txt
  S3_PREFIX_FILE=/opt/emr/s3_prefix.txt
  SNAPSHOT_TYPE_FILE=/opt/emr/snapshot_type.txt
  RUN_ID=1
  DATE=$(date '+%Y-%m-%d')
  STATUS="In-Progress"
  CURRENT_STEP=""
  CLUSTER_ID=`cat /mnt/var/lib/info/job-flow.json | jq '.jobFlowId'`
  CLUSTER_ID=$${CLUSTER_ID//\"}

  FINAL_STEP_NAME="flush-pushgateway"

  while [[ ! -f $CORRELATION_ID_FILE ]] && [[ ! -f $S3_PREFIX_FILE ]] && [[ ! -f $SNAPSHOT_TYPE_FILE ]]
  do
    sleep 5
  done

  CORRELATION_ID=`cat $CORRELATION_ID_FILE`
  S3_PREFIX=`cat $S3_PREFIX_FILE`
  SNAPSHOT_TYPE=`cat $SNAPSHOT_TYPE_FILE`
  DATA_PRODUCT="ADG-$SNAPSHOT_TYPE"

  while [ ! -f $STEP_DEATILS_DIR/*.json ]
  do
    sleep 5
  done

  JSON_STRING=`cat /opt/emr/dynamo_schema.json`
  JSON_STRING=`jq '.Correlation_Id.S = "'$CORRELATION_ID'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.DataProduct.S = "'$DATA_PRODUCT'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.Date.S = "'$DATE'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.Run_Id.N = "'$RUN_ID'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.Status.S = "'$STATUS'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.Cluster_Id.S = "'$CLUSTER_ID'"'<<<$JSON_STRING`
  JSON_STRING=`jq '.S3_Prefix.S = "'$S3_PREFIX'"'<<<$JSON_STRING`


  processed_files=()
  dynamo_put_item() {
    JSON_STRING=$1
    aws dynamodb put-item  --table-name ${dynamodb_table_name} --item "$JSON_STRING"
  }
  check_step_dir() {
    cd $STEP_DETAILS_DIR
    for i in $STEP_DETAILS_DIR/*.json; do
      if [[ "$${processed_files[@]}" =~ "$${i}" ]]; then
        continue
      fi
      state=$(jq -r '.state' $i)
      while [[ "$state" != "COMPLETED" ]]; do
        step_script_name=$(jq -r '.args[0]' $i)
        CURRENT_STEP=$(echo "$step_script_name" | sed 's:.*/::' | cut -f 1 -d '.')
        JSON_STRING=`jq '.CurrentStep.S = "'$CURRENT_STEP'"'<<<$JSON_STRING`
        state=$(jq -r '.state' $i)
        if [[ "$state" == "FAILED" ]] || [[ "$state" == "CANCELLED" ]]; then
          log_wrapper_message "Failed. Step Name: $CURRENT_STEP, Step status: $state"
          JSON_STRING=`jq '.Status.S = "FAILED"'<<<$JSON_STRING`
          dynamo_put_item "$JSON_STRING"
          exit 0
        fi
        if [[ "$CURRENT_STEP" == "$FINAL_STEP_NAME" ]] && [[ "$state" == "COMPLETED" ]]; then
          JSON_STRING=`jq '.Status.S = "COMPLETED"'<<<$JSON_STRING`
          dynamo_put_item "$JSON_STRING"
          exit 0
        fi
        if [[ $PREVIOUS_STATE != $state ]] && [[ $PREVIOUS_STEP != $CURRENT_STEP ]]; then
          
          dynamo_put_item "$JSON_STRING"
          log_wrapper_message "Success. Step Name: $CURRENT_STEP, Step status: $state"
          processed_files+=( $i )
        else
          sleep 5
        fi
        PREVIOUS_STATE=$state
        PREVIOUS_STEP=$CURRENT_STEP
      done
    done
    check_step_dir
  }

  #Check if row for this correlation ID already exists - in which case we need to increment the Run_Id
  response=`aws dynamodb get-item --table-name ${dynamodb_table_name} --key '{"Correlation_Id": {"S": "'$CORRELATION_ID'"}, "DataProduct": {"S": "'$DATA_PRODUCT'"}}'`
  if [[ -z $response ]]; then
    dynamo_put_item "$JSON_STRING"
  else
    STATUS=`echo $response | jq -r .'Item.Status.S'`
    log_wrapper_message "Status from previous run $STATUS"
    if [[ "$STATUS" == "FAILED" ]]; then
      log_wrapper_message "Previous failed status found, creating step_to_start_from.txt"
      CURRENT_STEP=`echo $response | jq -r .'Item.CurrentStep.S'`
      echo $CURRENT_STEP >> /opt/emr/step_to_start_from.txt
    fi   

    RUN_ID=`echo $response | jq -r .'Item.Run_Id.N'`
    RUN_ID=$((RUN_ID+1))
    JSON_STRING=`jq '.Run_Id.N = "'$RUN_ID'"'<<<$JSON_STRING`
    JSON_STRING=`jq '.Date.S = "'$DATE'"'<<<$JSON_STRING`
    dynamo_put_item "$JSON_STRING"
  fi
  log_wrapper_message "Updating DynamoDB with CORRELATION_ID: $CORRELATION_ID and RUN_ID: $RUN_ID"

  #kick off loop to process all step files
  check_step_dir

) >> /var/log/adg/update_dynamo_sh.log 2>&1
