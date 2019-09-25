#from requests import Request , Session
import requests
import json
import re
import yaml
import smtplib
import os
import datetime
import sys
import time
import traceback
import mailer
import delete_agent
import delete_vm
import delete_vm_via_uuid

#Loads config in a global variable
config = yaml.load(open(os.getcwd()+"/script-config/config.yaml",'r'))['Config']

#Because switch case does not exists 
frequency = {}
locations = {}

#Headers stores http headers (for authentication and content type)
headers= {"Content-Type" : "application/json", "Authorization" : "BASIC "+sys.argv[3]+""}
server = sys.argv[1]
server_port = sys.argv[2]
error_recipient = sys.argv[4]
error_sender = sys.argv[5]
maildomain = sys.argv[6]
mailserver = sys.argv[7]
requests.packages.urllib3.disable_warnings()
emailer = ""
agentF = ""
vmF = ""
vmuuidF = ""
baseurl = "https://"+server+":"+server_port+config['networker_urls']['base']


## @main Main method for handeling backup type selection
def main():
 global emailer,error_recipient,agentF,config,locations,error_sender,maildomain,baseurl,mailserver
 buildFrequencyMapping()
 buildLocationMapping()
 emailer = mailer.Mailer("false",error_recipient,mailserver,error_sender,"",maildomain)
 agentF = delete_agent.Agent(baseurl,headers,config['networker_urls'])
 vmF = delete_vm.VM(headers,baseurl,config['networker_urls'])
 vmuuidF = delete_vm_via_uuid.VMuuid(headers,baseurl,config['networker_urls'])
 print ("-----------------------Delete script has started------------------------")
 try:
   for filename in os.listdir(os.getcwd() + "/delete"):
    if ".yaml" in filename :
     try:
      yamlD = yaml.load(open(os.getcwd()+"/delete/"+filename,'r'))
      if yamlD != None and 'Client' in yamlD:
       for x in range(0,len(yamlD['Client'])) :
        try:
         if yamlD['Client'][x]['backupType'] == "Filesystem" :
            knownClient = agentF.getClient(yamlD['Client'][x]['hostname'])
            if knownClient != None and len(knownClient) > 0 :
                agentF.deleteClient(knownClient[0]['resourceId']['id'])
            else:
               print (yamlD['Client'][x]['hostname'] + " could not be found in networker, maybe it is already deleted?")
         elif yamlD['Client'][x]['backupType'] == "VM":
                result = vmF.searchForVM(yamlD['Client'][x]['hostname'])
                if result != None :
                        location = ""
                        if "location" in yamlD['Client'][x] :
                                location = locations[yamlD['Client'][x]['location'].lower()] + "_"
                        group=yamlD['Client'][x]['retentionclass']+"_VM_"+location+frequency[yamlD['Client'][x]['frequency'].lower()]+yamlD['Client'][x]['starttime']
                        vmF.deleteVM(result['uuid'],group,result['vCenter'])
        except:
          if len(yamlD['Client']) > 0 :
                emailer.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['Client'][x]['hostname'])
          else: 
                emailer.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['Client'])
      elif yamlD != None and 'ToDelete' in yamlD:
       	for x in range(0,len(yamlD['ToDelete'])) :
                try:
                        if yamlD['ToDelete'][x]['backupType'] == "VM" :
                                group=yamlD['ToDelete'][x]['group']
                                vmuuidF.deleteVM(yamlD['ToDelete'][x]['uuid'],group)
                except:
                        emailer.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['ToDelete'][x]['uuid'])
     except:
       emailer.send_error_mail(str(traceback.format_exc()))
 except:
  print ("something went wrong")
  print ("sending error message")
  emailer.send_error_mail(str(traceback.format_exc()))

## @buildFrequencyMapping
def buildFrequencyMapping():
        global frequency,config
        for freq in yaml.load(open(os.getcwd()+"/"+config['files']['basedir']+config['files']['frequencyFile'],'r'))['frequencys']:
                frequency[freq['name']] = freq['value']

## @buildLocationMapping
def buildLocationMapping():
        global locations,config
        for loc in yaml.load(open(os.getcwd()+"/"+config['files']['basedir']+config['files']['locations'],'r'))['locations']:
                locations[loc['name']] = loc['value']

main()

