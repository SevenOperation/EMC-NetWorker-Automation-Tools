# EMC-NetWorker-Automation-Tools
Inherits all NetWorker Automation Tools

The things the automation can archive are listed below

* Read yaml config files and create/update backup entrys for them
* Delete backup entrys if files are in a delete folder
* Delete vm based on uuid
* Monitoring all jobs (failed or success)
* Send report mails which gives you feedback if an backup was made or what went wrong
* Send graphite metrics to see how many backups succeeded or failed

Below here there are things listed which onyl works with vmware vcenter in a version where the rest api is available.

* Start an restore process for a vm for testing and monitor if it failes or succeeds
* Start an block based backup restore test and wait for it to succeed

## Below is an example of how the backup entry group is defined in the yaml

Retentionclass_backupType_frequency_location_startime

Please name them like after the node name. As an example: machinename.dns should have the config name machinename.yaml. Now of course we need to get Data into this config. As an example the yaml file should look like this for a filesystem backup afterwards:

## Configuration Parameter

| Attribute           | Example                                     | Description                                                                                                                                                                                                                     |
| ------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| aliases             | ['hostname']                                | This is a mandatory list of aliases, only for backupType `Agent`.                                                                                                                                                                         |
| hostname            | 'hostname.management.local'                 | Here you have to specify the full specified host name, FQDN would be great. If backupType is `VM` this needs to match the Name in `VMWare`.                                                                                     |
| mail                | ['group-email@domain.de']                 | A list of mail addresses which get informed when something is not right with the node, the mails are seperated by ',' example: ['mail','anothermail',...]                                                                       |
| owner               | ['Name of the contact']                     | This is the Name which will show up in the Mail so please don't leave it empty and try to have them in the same order like the mails.                                                                                           |
| starttime           | '05'                                        | This represents the starttime when the backup should begin, valid times are only `hours` and only two values example: '1' is not valid '01' valid the backup would begin at 01:00                                               |
| clientType          | 'AGENT'                                     | Just leave it like this.                                                                                                                                                                                                        |
| parallelism         | 12                                          | Just leave it like this, only for `Agent` Backups                                                                                                                                                                               |
| scheduledBackup     | 'true'                                      | If you want to add this node but you don't want any backups to be made right now just change this to 'false'. Please make sure you only used lower letters                                                                      |
| frequency           | 'Every Day'                                 | When a backup should be made valid Options are specified in the frequencys.yaml. Please specify the values as written even the system is case insensitive                               |
| retentionclass      | 'R1'                                        | This Defines how long the backup should be saved , valid options are: `'R1'`, `'R2'` and `'R3'`                                                             |
| backupType          | 'Filesystem'                                | Here you specify whether you want to save a VM (Snapshot) or only specific Filesystems. Valid options: `'VM'` or `'Filesystem'`                                                                                                 |
| vcenter             | ''                                          | the vcenter the vm is in|
| saveSets            | [''] | Here you specify which filesystems should get a backup please make sure you want to save filesystems on windows machine to use "\\" instead of "\\" Examples: "C:\\", "D:\\" 'DISASTER_RECOVERY:' or use 'C:\' instead, only for backupType `Agent`. |
| location            | ''                                          | **Optional** parameter valid values: 'Berlin' and 'Hamburg' otherwise don't add it. When empty or missing München is assumed                                                                                                        |
| error_report        | 'true'                                      | If this is set to false or this is missing, all contacts , specified in mail will get reports even when the backup is succeeded.                                                                                                |
| location            | ''                                          | **Optional** parameter valid values: 'Berlin', 'Hamburg' and 'TUV' otherwise don't add it. When empty or missing München is assumed                                                                                                        |
| parallelSaveStreams | 'false'                                     | **Optional** parameter valid values: 'true' and 'false' otherwise don't add it. When missing 'false' is assumed. This parameter is only for backupType `Agent`.|                                  
| preCommand            | ''                                          | **Optional** parameter (String) **Only for Clients**|
| postCommand            | ''                                          | **Optional** parameter (String) **Only for Clients**|
| blockBasedBackup      | 'false'                                      |**Optional** Set to true to enable block based backup, otherwise set to false or don't add it to the yaml, then false will be assumed **Only for Clients with volumes above 3TB and a lot of files **|

## Examples

### File Agent, File agent_example.yaml:

    Client:
     -
      aliases: ['Host']  
      hostname: 'host.domain.com'
      mail: ['group-email@domain.com']
      owner: ['Name of the contact']
      starttime: '05'
      clientType: 'AGENT'
      parallelism: 12
      error_report: 'true'
      scheduledBackup: 'true'
      frequency: 'Every Day'
      retentionclass: 'R1'
      backupType: 'Filesystem'
      saveSets: ['/']
      location: ''
      parallelSaveStreams: 'true'
      preCommand: ''
      postCommand: ''

### VM Snapshot, File: vm_example.yaml:

    Client:
     -
      hostname: 'VM'
      mail: ['group-email@domain.com']
      owner: ['Name of the contact']
      starttime: '07'
      frequency: 'Every Day'
      retentionclass: 'R1'
      backupType: 'VM'
      vcenter: ''
      error_report: 'true'
      location: ''
