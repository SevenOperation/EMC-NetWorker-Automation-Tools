# -*- coding: utf-8 -*-
from requests import Request , Session
import requests
import json
import yaml
import smtplib
import os
import datetime
import sys
import time
import traceback
from collections import OrderedDict
import random
import socket
import ast

config = yaml.load(open("config.yaml",'r'))['Config'] # Loads config.yaml in to a global variable
now = datetime.datetime.now() #Current Time
backup_states = {} # To store the data "state" and "info" about a backup process
requests.packages.urllib3.disable_warnings() #dissables unsecure ssl warnings
#Headers stores http headers (for authentication and content type)
headers= {"Content-Type" : "application/json", "Authorization" : "BASIC "+ sys.argv[3]+""} #stores the informations used to communicate with the networker restapi
vmWareHeaders = {} #stores the information returned after authenticating against vcenter call the api
vmware_user = sys.argv[8] #stores the vm user used for authenticating agianst the vcenter
vmware_password = sys.argv[9] #stores the vmware password to authenicate agianst the vcenter
modes = {'datadomain':'backup','cloud':'s3 clone','remote_datadomain':'datadomain clone'} #Used to map mode parameter to networker backup naming
modes_reversed = {'backup':'datadomain','s3 clone':'cloud','datadomain clone':'remote_datadomain','aws_clone':'cloud'} 
rest_server = sys.argv[1] #ip or dns from the networkers restapi
server_port = sys.argv[2] #port of the networkers restapi
error_recipient = sys.argv[4] #full mail address which will recieve error mails
cleanup = sys.argv[5].lower() #stores a string which represents a boolean to decide wether the restored vm should be removed afterwards or not
vcenter = "" #stores the vcenter name on which the vm we want to restore is right now
mode = sys.argv[6] #stores a string which will be used to decide from where the backup should be retrieved
oldest = sys.argv[7] #stores an boolean to decide wether the oldest backup or the backup from x days before should be used
proxies={"https":None}
backup_from_days_before = int(sys.argv[10]) #stores an int which determines which backup should be restored
maxBackupSize = int(sys.argv[11]) #stores an int which determines how big the backup is allowed to be (in GB)
maildomain = sys.argv[12] #stores the domain part of the email address which will be used for sending example: @web.de
error_sender = sys.argv[13] #stores the name part of the email address which will be used for sending error mails example: recover_error
mailserver = sys.argv[14] #stores the mailserver which should be used for sending mails
debug = sys.argv[15].lower() #stores a boolean which determines wether debug output should be shown or not
backup_number = 0 #is used to determine on which postion the backup was found we will use
restoredSize = 0 #stores the actual backup size which will be sended to graphite to display how many data we have restored
baseurl = "https://"+rest_server+":"+server_port+config['networker_urls']['base'] #stores the baseurl for every request against the networker
send_graphiteMetrics = sys.argv[16].lower() #stores an boolean to decide wether the graphite metrics should be send or not
backupNotFoundMessage = "ERROR No backup found for that Date"
vcenter_ip_address = sys.argv[17]
graphite_server = sys.argv[18]
graphite_port = int(sys.argv[19])
graphite_baseurl = sys.argv[20]
searchTimeout = int(sys.argv[21])
vcenter_name = sys.argv[22]

#Main method for handeling backup type selection
def main():
	global cleanup,mode,modes, searchTimeout
	if isNetWorkerReachable() and isVCenterReachable():
		print ("Skript is starting")
		if mode in modes:
			print ("The recover mode is: " + mode)
			mode = modes[mode]
			if cleanup == 'true':
				cleanup = True
			else:
				cleanup = False
			vms = getVMS()
			vm =  vms[random.randint(0,len(vms) -1)]['name']
			print(vm)
			result = searchForVM(vm)
			if result != None :
				authenticate('<your location name>')
				vm_id =  getVMFromAPI(vm+"_recovered",'<your location name>',1) 
				if vm_id != "" :
					shutdown(vm_id,'<your location name>')
					delete(vm_id,'<your location name>')
				if getVM_backup(result) == "ERROR no Backup found":
					return
				vm_id = getVMFromAPI(vm+"_recovered",'<your location name>',searchTimeout)
				if vm_id == "":
					send_error_mail("ERROR: VM was not found after 2h script will be stopped")
					print("ERROR VM was not found after 2h script will be stopped")
					return
	else:
		print("Networker or VCenter is not reachable")
		send_metrics_to_graphite(0)
		send_error_mail("NetWorker or VCenter is not reachable")

## @send_error_mail Sends a mail if an error occur to the mail defined in teamcity as error_mail
def send_error_mail(error) :
	global error_sender, maildomain,error_recipient,mailserver,debug
	try:
		sender = error_sender + maildomain
		server = smtplib.SMTP(mailserver,25,"mail_domain",60)
		if debug == "true":
			server.set_debuglevel(1)
		data = "subject: Error \n\n" + " Fehler in backup-recover-test \n Fehlermeldung: " + error 
		server.sendmail(sender,error_recipient,data)
		server.quit()
	except:
		print ("WARNING: WARNING mail could not be send" + error)
		print ("Fehler 2: " + str(traceback.format_exc()))
		return

## @checkBackupSize checks if the backupsize is not bigger then specified
def checkBackupSize(backups):
	global maxBackupSize, backup_from_days_before , oldest , backup_number, mode,restoredSize, backupNotFoundMessage
	if oldest.lower() == "false":
		backupFound = False
		backup_number = 0
		restore_backup_from_time = datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d"),"%Y-%m-%d") - datetime.timedelta(days=backup_from_days_before)
		for backup_data in backups['backups'] :
			oldest_time = backup_data['completionTime'].split('T')
			backup_time = datetime.datetime.strptime(oldest_time[0],"%Y-%m-%d")
			print ("Restore backup from: "+ str(restore_backup_from_time))
			print ("Found backup from: "+ str(backup_time))
			backup_number += 1
			if backup_time == restore_backup_from_time :
				print ("Backup found let's see if it is not to big")
				if backup_data['size']['value'] / 1000000000 <= maxBackupSize :
					print ("Backup size is ok ("+str(backup_data['size']['value']/1000000000)+"GB)") 
					backupFound = True
					restoredSize = backup_data['size']['value'] / 1000000000
					break
				else:
					print ("Backup size is to big. Allowed: " + str(maxBackupSize) + "GB Found: " + str(backup_data['size']['value'] / 1000000000)+ "GB")
					backupNotFoundMessage = "ERROR Found a backup from that date but it is exceeding the allowed backup size for the restore test. Allowed are " + str(maxBackupSize) + "GB but found one with " +str(backup_data['size']['value'] / 1000000000)+ "GB"
		return backupFound
	else:
		if backups['backups'][len(backups) - 1]['size']['value'] / 1000000000 <= maxBackupSize :
			print ("Found a backup")
			print ("using oldest Backup in mode " + str(mode))
			backupFound = True
			backup_number = len(backups) - 1
			mode = 0
		return backupFound

##  @getVM_backup Fills the array backup_states with the last backup state and the info from a VM
def getVM_backup(uuid):
	global oldest, mode, backup_from_days_before, maxBackupSize, a,baseurl, backupNotFound
	if uuid != None:
		data=""
		recover_link = baseurl+"vmware/vcenters/"+uuid['vCenter']+"/protectedvms/"+uuid['uuid']+"/backups"
		backup_list = requests.request("GET",recover_link,data=data,headers=headers,verify=False, timeout=30)
		backups = json.loads(backup_list.text)
		print ("Get backup from VM: " + uuid['hostname'])
		if backups['count'] != 0 :
			if checkBackupSize(backups):
				backup = backups['backups'][backup_number]
				print ("-----------------------Informtaionen---------------------")
				print ("UUID: " + str(uuid['hostname']) + " CreationTime: "+backup['completionTime'])
				print (backup)
				print ("-----------------------------Informationen ende--------------------")
				informations = ""
				for info in backup['attributes'] :
					if info['key'] == "*vm_info" :
						informations = json.loads(info['values'][0])
						break;
				found_id = False
				for info in backup['attributes'] :
					if info['key'] == "*policy action name":
						available_modes = {}
						for value in info['values']:
							available_modes[value.split(':')[0]]=value.split(':')[1]
						if mode in available_modes :
							mode_id = available_modes[mode]
						else:
							send_error_mail("Mode "+modes_reversed[mode]+" can not be used because there is no backup available from this source, switching to " + modes_reversed[list(available_modes.keys())[len(list(available_modes.keys()))-1]])
							mode_id = available_modes[available_modes.keys()[len(available_modes.keys())-1]]
						if " " in mode_id:
							mode_id = mode_id.split(' ')[1]
						found_id = True
				if mode_id == "" or mode_id == " ":
					found_id = False
				if found_id == False: #sometimes the networker does not return policy action names if thats the case this handels our fallback and switches to a other backup source 
					if mode == 'datadomain clone' and len(backup['instances']) >=2:
						for b in backup['instances']:
							if b['clone'] == 'true':
								mode_id = b['id']
					else:
						mode_id = backup['instances'][0]['id']
						send_error_mail("Mode "+modes_reversed[mode]+" can not be used because there is no backup available from this source, switching to datadomain")
						mode = "datadomain"
				vmname = '"vmName":"'+uuid['hostname']+"_recovered" +'"' 
				clustercompute = '"clusterComputeResourceMoref":"'+ informations['cluster-compute-resource'] +'"'
				datacenter = '"datacenterMoref":"' + informations["datacenter"] + '"'
				job = '"jobName":"backup-recover-test"'
				vCenter = '"vCenterHostname":"'+informations["vcenter-name"]+'"'
				power = '"powerOn":true'
				reconnect = '"reconnectNic":false'
				disks = backup['vmInformation']['disks']
				datastoreMoref = ""
				datastoreMoref=backup['vmInformation']['datastoreMoref']
				for d in range(0,len(disks)):
					del disks[d]['sizeInKb']
					del disks[d]['datastoreName']
					del disks[d]['thinProvisioned']
				disks = json.dumps(disks)
				print ("Mode is: " + str(mode))
				recover_link += "/" + backup['id'] + "/instances/"+mode_id
				print (recover_link)
				data = ""
				if mode == 's3 clone' :
					data = '{"recoverMode":"New",'+datacenter+',"datastoreMoref":"'+datastoreMoref+'","disks":'+disks+','+power+','+reconnect+','+vmname+','+vCenter+','+job+','+clustercompute+',"stagingPool":"<your staging pool>","resourcePoolMoref":""}'
				else:
					data = '{"recoverMode":"New",'+datacenter+',"datastoreMoref":"'+datastoreMoref+'","disks":'+disks+','+power+','+reconnect+','+vmname+','+vCenter+','+job+','+clustercompute+',"resourcePoolMoref":""}'
				print (data)
				backup_list = requests.request("POST",recover_link+"/op/recover" ,data=data,headers=headers,verify=False)
				print(backup_list.text)
				print("##teamcity[setParameter name='restoringVM' value='"+uuid['hostname']+"']")
				if backup_list.status_code > 201:
					print (backup_list.text)
					print (backup_list.status_code)
					send_metrics_to_graphite(0)
					send_error_mail('Something in the communication with the networker went wrong ' + backup_list.status_code + " " + backup_list.text)
					print ("ERROR Something went wrong")
			else:
				send_metrics_to_graphite(0)
				send_error_mail(backupNotFoundMessage)
				print (backupNotFoundMessage)
		
		else:
			send_metrics_to_graphite(0)
			send_error_mail('No Backup could be found. No backups exists or machine was not backuped yet')
			print ("ERROR no Backup found")
			return ("ERROR no Backup found")

## @searchForVM Searches all vcenter for a specific vm and returns uuid
def searchForVM(vm) :
    global vcenter, baseurl
    data=''
    r = requests.request(config['networker_urls']['vmcenter']['get']['method'],baseurl+config['networker_urls']['vmcenter']['get']['path']+'?fl=hostname',data=data,headers=headers,verify=False)
    vmCenters = json.loads(r.text)['vCenters']
    print('The following VM Centers will be searched for the VM '+ vm )
    if 'vcenter' in vm and vcenter != "":
      print(" Search in explicit defined vmCenter: " + vm['vmcenter'] + " begins")
      r = requests.request(config['networker_urls']['vmcenter']['get']['method'],baseurl+config['networker_urls']['vmcenter']['get']['path']+vm['vcenter']+'/vms?fl=hostname,uuid,name',data=data,headers=headers,verify=False)
      vms = json.loads(r.text)['vms']
      for x in range(0,len(vms)) :
       if vms[x]['hostname'] == vm or vms[x]['name'] == vm :
        print("  VM was found and has the following uuid: " + vms[x]['uuid'])
        result = {'uuid':vms[x]['uuid'],'vCenter':vm['vcenter']}
        print("##teamcity[setParameter name='vmvCenter' value='"+vm['vcenter']+"']")
        return result
      print("VM was not found in the specified vcenter now all will be searched")
    for i in range(0,len(vmCenters)) :
     print(" Search in VM Center " + vmCenters[i]['hostname'] + " begins")
     r = requests.request(config['networker_urls']['vmcenter']['get']['method'],baseurl+config['networker_urls']['vmcenter']['get']['path']+vmCenters[i]['hostname']+'/vms?fl=hostname,uuid,name',data=data,headers=headers,verify=False)
     vms = json.loads(r.text)['vms']
     for x in range(0,len(vms)) :
      if vms[x]['hostname'] == vm or vms[x]['name'] == vm :
       print("  VM was found and has the following uuid: " + vms[x]['uuid'])
       vcenter = vmCenters[i]['hostname']
       result = {'uuid':vms[x]['uuid'],'vCenter':vmCenters[i]['hostname'], 'hostname':vm}
       print("##teamcity[setParameter name='vmvCenter' value='"+vmCenters[i]['hostname']+"']")
       return result
    send_metrics_to_graphite(0)
    send_error_mail('The VM does not exists')
    print("ERROR The VM does not exsits\n")
    return

## @authenticate does the authentication process against vcenter
def authenticate(location):
	global vmWareHeaders, vcenter, proxies, vmware_user, vmware_password
	print ("Authenticate against Automation Rest api from vcenter")
	print (vcenter)
	try:
		req = requests.request('POST','https://'+vcenter+'/rest/com/vmware/cis/session',auth=(vmware_user,vmware_password),proxies=proxies,verify=False)
		vmWareHeaders={'vmware-api-session-id':json.loads(req.text)['value']}
		if req.status_code > 201:
			send_error_mail('Authentication against vcenter failed')
			print ("ERROR Authentication against vcenter failed")
	except:
		send_error_mail('Authentication against vcenter failed: ' + str(traceback.format_exc()) )
         
## @getVMFromAPI getsVM from vcenter
def getVMFromAPI(vm_name, location , timeout=480):
	global vmWareHeaders, vcenter, proxies
	print ("Search " + vm_name + " in vcenter " + vcenter)
	if location.lower() == '<your location>' :
		found = False
		vm = ""
		while not found and timeout > 0: 
			time.sleep(60) 
			req = requests.request('GET','https://'+vcenter+'/rest/vcenter/vm?filter.names.1='+vm_name+'',proxies=proxies,headers=vmWareHeaders,verify=False)
			print (req.text)
			print (req.status_code)
			timeout -= 1
			if req.status_code == 200 and len(json.loads(req.text)['value']) > 0:
				vm = json.loads(req.text)['value'][0]['vm']
				found = True
			else:
				print ("VM Not found trying again in 1 Minute")
		return vm

## @shutdown shuts the vm down
def shutdown(vm,location):
	global vcenter, vmWareHeaders, proxies
	print ("Shutting down recovered VM")
	req = requests.request('POST','https://'+vcenter+'/rest/vcenter/vm/'+vm+'/power/stop',headers=vmWareHeaders,proxies=proxies,verify=False)
	time.sleep(60) 

## @delete deletes the vm
def delete(vm,location):
	global vcenter, vmWareHeaders, proxies
	print ("Starting Cleanup of recovered VM")
	req = requests.request('DELETE','https://'+vcenter+'/rest/vcenter/vm/'+vm,headers=vmWareHeaders,proxies=proxies,verify=False)
	time.sleep(60) 

## @isVCenterReachable checks if a connection to the vcenter can be established
def isVCenterReachable():
	global proxies, vmware_user, vmware_password, vcenter_ip_address
	try:
		req = requests.request('POST','https://'+vcenter_ip_address+'/rest/com/vmware/cis/session',auth=(vmware_user,vmware_password),proxies=proxies,verify=False,timeout=60)
		if req.status_code > 226 :
			print ("VCenter not reachable")
			print (req.text)
			return False
		return True
	except:
		print ("Connection to VCenter failed: " + str(traceback.format_exc()))
		send_error_mail("Connection to VCenter failed:" + str(traceback.format_exc()))

## @isNetWorkerReachable checks if a connection to the Networker can be Established
def isNetWorkerReachable():
	global baseurl
	try:
		result = requests.request("GET",baseurl,headers=headers,verify=False,timeout=60)
		if result.status_code > 226 :
			print ("NetWorker not reachable")
			return False
		return True
	except:
		print ("Connection to NetWorker failed: " + str(traceback.format_exc()))
		send_error_mail("Connection to NetWorker failed:" + str(traceback.format_exc()))

## @send_metrics_to_graphite creates metric for graphite
def send_metrics_to_graphite(success):
	global restoredSize,send_graphiteMetrics, graphite_server, graphite_port, graphite_baseurl
	graphite_port = int(graphite_port)
	if send_graphiteMetrics == "true":
		timestamp = int(time.mktime(now.timetuple()) + now.microsecond / 1E6)
		print ("-------------------------Metrics--------------------------")
		try:
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(20)
			s.sendall((graphite_baseurl+".restored " + str(success) +" "+ str(timestamp) + "\n").encode())
			s.close()
			if success == 1:
				s = socket.socket()
				s.connect((graphite_server, graphite_port))
				s.settimeout(10)
				s.sendall((graphite_baseurl+".restoredSize " + str(restoredSize) +" "+ str(timestamp) + "\n").encode())
				s.close()
		except:
			send_error_mail(str(traceback.format_exc()))

def getVMS():
	global headers,proxies,baseurl
	req = requests.request('GET',baseurl+'vmware/vcenters/'+vcenter_name+'/protectedvms',headers=headers,proxies=proxies,verify=False,timeout=60)
	vms = json.loads(req.text)['vms']
	return vms 
main() ## Runs the main Method
