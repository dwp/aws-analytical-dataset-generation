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
      InstanceType: "${instance_type_master}"
  - InstanceFleetType: "CORE"
    Name: CORE
    TargetOnDemandCapacity: ${core_instance_capacity_on_demand}
    TargetSpotCapacity: ${core_instance_capacity_spot}
    LaunchSpecifications:
      SpotSpecification:
        BlockDurationMinutes: ${spot_block_duration_minutes}
        TimeoutDurationMinutes: ${spot_timeout_duration_minutes}
        TimeoutAction: "SWITCH_TO_ON_DEMAND"
    InstanceTypeConfigs:
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type_core_one}"
      BidPriceAsPercentageOfOnDemandPrice: 100
      WeightedCapacity: ${instance_type_weighting_core_one}
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type_core_two}"
      BidPriceAsPercentageOfOnDemandPrice: 100
      WeightedCapacity: ${instance_type_weighting_core_two}
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type_core_three}"
      BidPriceAsPercentageOfOnDemandPrice: 100
      WeightedCapacity: ${instance_type_weighting_core_three}
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type_core_four}"
      BidPriceAsPercentageOfOnDemandPrice: 100
      WeightedCapacity: ${instance_type_weighting_core_four}
    - EbsConfiguration:
        EbsBlockDeviceConfigs:
        - VolumeSpecification:
            SizeInGB: 250
            VolumeType: "gp2"
          VolumesPerInstance: 1
      InstanceType: "${instance_type_core_five}"
      BidPriceAsPercentageOfOnDemandPrice: 100
      WeightedCapacity: ${instance_type_weighting_core_five}
