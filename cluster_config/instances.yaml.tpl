---
Instances:
  KeepJobFlowAliveWhenNoSteps: ${keep_cluster_alive}
  AdditionalMasterSecurityGroups:
  - "${add_master_sg}"
  AdditionalSlaveSecurityGroups:
  - "${add_slave_sg}"
  Ec2SubnetIds: ${jsonencode(split(",", subnet_ids))}
  EmrManagedMasterSecurityGroup: "${master_sg}"
  EmrManagedSlaveSecurityGroup: "${slave_sg}"
  ServiceAccessSecurityGroup: "${service_access_sg}"
  InstanceFleets:
  - InstanceFleetType: "MASTER"
    Name: MASTER
    TargetOnDemandCapacity: 1
    InstanceTypeConfigs:
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type}"
  - InstanceFleetType: "CORE"
    Name: CORE
    TargetOnDemandCapacity: ${no_core_nodes}
    InstanceTypeConfigs:
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${core_instance_type_1}"
      WeightedCapacity: ${weightedcapacity_1}
    InstanceTypeConfigs:
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${core_instance_type_2}"
      WeightedCapacity : ${weightedcapacity_2}
