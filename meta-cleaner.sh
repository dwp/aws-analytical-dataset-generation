#!/usr/bin/env bash

export CLUSTER_ID=$(cat /mnt/var/lib/info/job-flow.json|jq -r ".jobFlowId")
export HBASE_META=${hbase_meta}
export METATABLE=${metatable_name}

echo "Removing all files from" $HBASE_META$CLUSTER_ID
aws s3 rm --recursive $HBASE_META$CLUSTER_ID
aws s3 rm  $HBASE_META$CLUSTER_ID'_$folder$'

echo "deleting dynamodb table" $METATABLE
#aws dynamodb delete-metadata
aws dynamodb delete-table --table-name $METATABLE

#echo "syncing s3"
#emrfs sync $HBASE_META