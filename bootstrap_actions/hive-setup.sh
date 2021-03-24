#!/bin/bash
set -euo pipefail
(
    # Import the logging functions
    source /opt/emr/logging.sh
    
    # Import and execute resume step function
    source /opt/emr/resume_step.sh

    function log_wrapper_message() {
        log_adg_message "$1" "hive-setup.sh" "$$" "Running as: $USER"
    }

    log_wrapper_message "Moving maria db jar to spark jars folder"
    sudo mkdir -p /usr/lib/spark/jars/
    sudo cp /usr/share/java/mariadb-connector-java.jar /usr/lib/spark/jars/

    log_wrapper_message "Setting up EMR steps folder"
    sudo mkdir -p /opt/emr/steps
    sudo chown hadoop:hadoop /opt/emr/steps

    log_wrapper_message "Creating init py file"
    touch /opt/emr/steps/__init__.py

    log_wrapper_message "Moving python steps files to steps folder"
    aws s3 cp "${python_logger}" /opt/emr/steps/.
    aws s3 cp "${python_resume_script}" /opt/emr/steps/.
    aws s3 cp "${generate_analytical_dataset}" /opt/emr/.

    log_wrapper_message "Generate fair scheduler xml"

cat > /opt/emr/fair-scheduler.xml <<FAIR_SCHEDULER_CFG
    <?xml version=”1.0"?>
    <allocations>
        <queue name="root">
            <schedulingPolicy>fair</schedulingPolicy>
            <aclSubmitApps> </aclSubmitApps>
            <aclAdministerApps>*</aclAdministerApps>
            <queue name="queue1">
                <schedulingPolicy>fair</schedulingPolicy>
                <aclSubmitApps>*</aclSubmitApps>
                <aclAdministerApps>*</aclAdministerApps>
            </queue>
            <queue name="queue2">
                <schedulingPolicy>fair</schedulingPolicy>
                <aclSubmitApps>*</aclSubmitApps>
                <aclAdministerApps>*</aclAdministerApps>
            </queue>
            <queue name="queue3">
                <schedulingPolicy>fair</schedulingPolicy>
                <aclSubmitApps>*</aclSubmitApps>
                <aclAdministerApps>*</aclAdministerApps>
            </queue>
        </queue>
        <defaultQueueSchedulingPolicy>fair</defaultQueueSchedulingPolicy>
        <queuePlacementPolicy>
            <rule name="specified" />
            <rule name="default" queue="root"/>
        </queuePlacementPolicy>
    </allocations>
FAIR_SCHEDULER_CFG

    sudo stop hadoop-yarn-resourcemanager
    sleep 10
    sudo start hadoop-yarn-resourcemanager

) >> /var/log/adg/hive_setup.log 2>&1


