#!/usr/bin/env bash

export CLUSTER_ID=$(cat /mnt/var/lib/info/job-flow.json|jq -r ".jobFlowId")
export HBASE_META=${hbase_meta}
echo "Removing all files from" $HBASE_META$CLUSTER_ID
aws s3 rm --recursive $HBASE_META$CLUSTER_ID
aws s3 rm --recursive $HBASE_META$CLUSTER_ID
aws s3 rm --recursive $HBASE_META$CLUSTER_ID"_$folder$"