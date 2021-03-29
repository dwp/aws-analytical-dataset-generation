# Cluster configuration

## Choices made

The choice was made that each EMR cluster should have its own configuration - this is because ADG Full and Incremental run different applications and configurations for one application would cause a negative effect on the other.
Therefore ADG Full and Incremental have individual configurations, `configuration` and `configuration-incremental` respectively.

## Useful information
AWS EMR provides Yarn timeline UI and Tez UI - this allows you to check the status, timings and logs of a task at a very granular level. Familiarise yourself with these interfaces.

## Configuration explanation

### Yarn configuration
At the lowest level, all applications on an EMR cluster are ran and controlled by Yarn. Through testing we saw that with a single yarn queue, applications were running FIFO and not utilising the full cluster.
We've created three yarn queues, `default` `appqueue` and `mrqueue`.

Each queue has a defined minimum percentage of cluster resources available to it, with a defined maximum burst capacity - which can be used if the task within that queue requires it and the other queues minimum capacity is not impacted.

For the `default` queue, that capacity is 5% with a burst of 10%.
For the `appqueue` queue, that capacity is 25% with a burst of 90%.
For the `mrqueue` queue, that capacity is 70% with a burst of 90%.

See Capacity Scheduler for more details.

*`mrqueue` means Map Reduce Queue. Mappers and reducers spawned by Tez are ran as seperate applications in Yarn. We can control the queue they use by the config setting `mapreduce.job.queuename`.

### Hive configuration
At the next level, HiveServer, which operates and controls Tez, has Tez container resource controls. We have set these according to the cluster size using:
`hive.tez.container.size` - The overarching Tez *task* container. The lower this value, the more task containers you can have. There is a fine balance of task requirement vs. number of tasks you'd like to have available to run at once.
`hive.tez.java.opts` - The java memory limit, must be 80% of `hive.tez.container.size`.

Vectorisation is disabled due to undiagnosed SQL failures that it causes.

### Tez configuration
Finally, at the highest level we have Tez configuration. Tez is responsible for organising and executing the tasks ran against Hive.
Tez has two elements to consider: Tez Application Master (known as Tez AM) and Tez tasks.
The Tez Application master to our understanding attempts to operate on a 1:1 ratio with the number of nodes in the cluster. 
This is controlled via a few configurations:

`tez.am.resource.memory.mb` - The amount of memory each Tez AM should have
`tez.am.launch.cmd-opts` - The java memory capacity of the Tez AM application, set to 80% of `tez.am.resource.memory.mb`.

The next consideration Tez task container, handles the task itself. As such, it requires enough resources to conduct the task required. ie. If a large data load is required, a high memory Tez task container will be required.
There is again a balance to find, between the number of Tez task containers you'd like vs. each containers resource capacity.

`tez.task.resource.memory.mb` - The amount of memory each Tez task should have

In additional to the memory configurations, the number of Tez containers spawned for the queue is configured by `hive.server2.tez.sessions.per.default.queue`.
Again, a fine balance of the number of Tez sessions to create across the cluster vs. the tasks resource requirement.

Tez default queue is set to `appqueue` in our configuration. Set the queue via `hive.server2.tez.default.queues`.
This parameter tells Tez which Yarn queue to assign tasks to. Note: If you set two queues here, Tez would randomly assign a task a Yarn queue, if one was not supplied in the original Hive command. If a queue is supplied, Tez honours the selection.

### LLAP Configuration
Hive 'Live Long and Process'

A good description of LLAP:

LLAP provides a hybrid execution model. It consists of a long-lived daemon which replaces direct interactions with the HDFS Data Node, and a tightly integrated DAG-based framework.
Functionality such as caching, pre-fetching, some query processing and access control are moved into the daemon. Small/short queries are largely processed by this daemon directly, while any heavy lifting will be performed in standard YARN containers.

Similar to the Data Node, LLAP daemons can be used by other applications as well, especially if a relational view on the data is preferred over file-centric processing. The daemon is also open through optional APIs (e.g., Input Format) that can be leveraged by other data processing frameworks as a building block.

Hive LLAP consists of the following component

Hive Interactive Server: Thrift server which provide JDBC interface to connect to the Hive LLAP.
Slider AM: The slider application which spawns, monitor and maintains the LLAP daemons.
TEZ AM query coordinator: TEZ Am which accepts the incoming the request of the user and execute them in executors available inside the LLAP daemons (JVM).
LLAP daemons: To facilitate caching and JIT optimization, and to eliminate most of the startup costs, a daemon runs on the worker nodes on the cluster. The daemon handles I/O, caching, and query fragment execution.

[Source](https://community.cloudera.com/t5/Community-Articles/Hive-LLAP-deep-dive/ta-p/248893)

For our configuration, we are controlling the number of LLAP instances across the cluster with `hive.llap.num-instances`, controlling the resources provided to LLAP with `hive.llap.percent-allocation`.
For `hive.llap.percent-allocation`, this is a percentage given in decimal form. eg 0.1 is 10%.

We've experienced and it's also spoken about in the above resource, that LLAP instances should be given almost if not all Yarn resources for the instances it belongs on.
LLAP performs better if the instances it has, can utilise the full resources of the node it resides on; rather than each node having an LLAP instance and a small percentage of resources.
We can assume that this is because LLAP suffers from noisy neighbours.

### Mappers and Reducers configuration
Mappers collect and orchestrate data. Reducers operate joins operations etc.

We have configured the Yarn queue that map reduce tasks use with `mapreduce.job.queuename`.

In addition to the Yarn queue capacity, which defines the maximum resources that can be used by map reducers; we have configured additional values.

`hive.exec.reducers.max` - To configure the maximum number of map reducers and single task can have. More is not always better. A balance must be found.
`yarn.app.mapreduce.am.resource.vcores` - The vCores per map reducer

Other configurations to consider, which affect the number of map reducers a task gets / requires:
`tez.grouping.min-size` & `tez.grouping.max-size`
These values define the minimum and maximum size of a split, for a task. We have seen Tez log information when we had set these values too high for the data it was processing. Look out for that!

[Source](https://cwiki.apache.org/confluence/display/TEZ/How+initial+task+parallelism+works)

### Capacity Scheduler
AWS EMR by default uses Yarn Capacity scheduler for its queues.

Traditional usage of the capacity scheduler allows for a clusters resources to be allocated departmentally, with an burstable capacity if the cluster is not being utilised, offering an elastic nature.
With the deprecation of 'Fair Scheduler', it's ordering policy has been implemented into capacity scheduler.

Capacity scheduler has three policies for ordering tasks:
First In First Out - A single job can utilise 100% of the clusters resources, only this application runs until it has completed.
Capacity scheduler - Allows for resource allocation with elastic maximum capacity.
Fair scheduler - Assigns resources to all tasks running across multiple queues, such that on average, they get a fair share of the clusters resources. Job priorities can be provided to sway the resource utilisation in favour of a job.

[Source](https://medium.com/@sohamghosh/schedulers-in-emr-6445180b44f6)
[Source](https://blog.cloudera.com/yarn-capacity-scheduler/)
[Source](https://hadoop.apache.org/docs/r1.2.1/capacity_scheduler.html)

Note: We believe by configuring three seperate queues, one which for map reducers, one for application tasks and one for default (all misc. tasks), we've seen the most noticeable speed improvement and greater utilisation of the cluster.

## How does Yarn, Hive and Tez link together
It took trial and error to understand this, so it's worth making a record to skip hours of pain.

Tez has its own queue system, tasks are added to that queue when submitted to Hive. In default configuration, Tez requires a default queue, aptly named `default`.
We have set it to `appqueue`, this is the same name as a Yarn queue.

Tez pushes applications directly to the Yarn queue(s) you specify. If those tasks spawn mappers or reducers, those mappers and reducers are configured to use the highest capacity queue `mrqueue`.
It is our understanding that mappers and reducers are the lowest denominator in the performance of the system. By increasing the resources available, the number of maximum mappers or reducers for a task and giving them the highest queue priority, they finish quickly and efficiently.
Once the mappers and reducers finish, they all the Tez task which is awaiting completion on the `appqueue` to finish also, therefore progressing two queues.

## Resources
https://cwiki.apache.org/confluence/display/TEZ/How+initial+task+parallelism+works
https://community.cloudera.com/t5/Community-Articles/Hive-LLAP-deep-dive/ta-p/248893
https://blog.cloudera.com/yarn-capacity-scheduler/
https://medium.com/@sohamghosh/schedulers-in-emr-6445180b44f6
https://hadoop.apache.org/docs/r1.2.1/capacity_scheduler.html
