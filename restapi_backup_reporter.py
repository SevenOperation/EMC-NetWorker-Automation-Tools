# -*- coding: utf-8 -*-

from requests import Request , Session
from email.mime.text import MIMEText
import requests
import json
import re
import yaml
import os
import datetime
import sys
import time
import traceback
import socket
from collections import OrderedDict
from operator import itemgetter
import mailer
import policie

config = yaml.load(open(os.getcwd()+"/script-config/config.yaml",'r'))['Config'] # Loads config.yaml in to a global variable
now = datetime.datetime.now() #Current Time
contacts_relation_to_backups = {} # Stores the mail address assoziated wit a list of Nodes
contacts_relation_to_owner = {} #Stores the mail address assoziated with a owner
backup_states = {} # To store the data "state" and "info" about a backup process
requests.packages.urllib3.disable_warnings()

#Because switch case does not exists we created dict's instead
frequency = {}
frequency_to_time = {}
locations = {}

#Headers stores http headers (for authentication and content type)
headers= {"Content-Type" : "application/json", "Authorization" : "BASIC "+ sys.argv[3]+""}

rest_server = sys.argv[1]
server_port = sys.argv[2]
ignore_directories = sys.argv[4]
error_recipient = sys.argv[5]
debug = sys.argv[6]
admin_report_recipient = sys.argv[7]
send_admin_report = sys.argv[8]
maildomain = sys.argv[9]
report_sender = sys.argv[10]
error_sender = sys.argv[11]

filesystems_failed = 0
filesystems_success = 0
vms_failed = 0
vms_success = 0
emailer = ""
mailserver = sys.argv[12]
send_graphiteMetrics = sys.argv[13].lower()
graphite_server = sys.argv[14]
graphite_port = sys.argv[15]
graphite_baseurl = sys.argv[16]
baseurl = "https://"+rest_server+":"+server_port+config['networker_urls']['base'] #stores the baseurl for every request against the networker

##  @main Main method for handeling backup type selection
def main():
	global emailer,maildomain,report_sender,error_sender,config,mailserver,backup_states
	emailer = mailer.Mailer(debug,error_recipient,mailserver,error_sender,report_sender,maildomain, admin_report_recipient)
	emailer.config = config
	if is_networker_available() :
		buildFrequencyMapping()
		buildLocationMapping()
		buildFrequencyToTimeMapping()
		for directorie,subdirs,filenames in os.walk(os.getcwd()):
			print (directorie)
			try:
				if isInIgnoreList(directorie) == False :
					for filename in filenames:
						if ".yaml" in filename:
							try:
								yamlD = yaml.load(open(directorie+"/"+filename,'r'))
								if yamlD != None and "Client" in yamlD:
									for x in range(0,len(yamlD['Client'])) :
										try:
											createRelations(yamlD['Client'][x])
											if yamlD['Client'][x]['backupType'] == 'Filesystem':
												getFilesystem_backup_state(yamlD['Client'][x])
											elif yamlD['Client'][x]['backupType'] == 'VM':
												getVM_backup_state(yamlD['Client'][x])
											else :
												getFilesystem_backup_state(yamlD['Client'][x])
										except:
											print ("something went wrong")
											print ("sending error message to developer maurice fernitz")
											emailer.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['Client'][x]['hostname'])
							except:
								emailer.send_error_mail(str(traceback.format_exc()))
			except:
				emailer.send_error_mail(str(traceback.format_exc()))
		send_metrics_to_graphite()
		print("Trying to send the report mails")
		emailer.report_send_email(contacts_relation_to_owner,backup_states,contacts_relation_to_backups)
		if send_admin_report.lower() == 'true':
			getServerProtectionReport()
			emailer.send_admin_report_mail(backup_states)
	else:
		print ("ERROR: Networker not reachable/available please make sure networker gui/restApi is reachable/available")




## @create_relations Fills a list with mail to vm association and owner to mail association
def createRelations(vm):
	zaehler = 0
	if "mail" in vm:
		for contact in vm["mail"] :
			if contact not in contacts_relation_to_backups:
				contacts_relation_to_backups[contact] = []
				contacts_relation_to_backups[contact].append(vm['hostname'])
				if zaehler < len(vm['owner']) and vm['owner'][zaehler] != "" :
					contacts_relation_to_owner[contact] = vm['owner'][zaehler]
				zaehler += 1
			else:
				contacts_relation_to_backups[contact].append(vm['hostname'])
				if zaehler < len(vm['owner']) and vm['owner'][zaehler] != "" :
					contacts_relation_to_owner[contact] = vm['owner'][zaehler]
				zaehler += 1
	elif "email" in vm:
		for contact in vm["email"] :
			if contact not in contacts_relation_to_backups:
				contacts_relation_to_backups[contact] = []
				contacts_relation_to_backups[contact].append(vm['hostname'])
				if zaehler < len(vm['owner']) and vm['owner'][zaehler] != "" :
					contacts_relation_to_owner[contact] = vm['owner'][zaehler]
				zaehler += 1
			else:
				contacts_relation_to_backups[contact].append(vm['hostname'])
				if zaehler < len(vm['owner']) and vm['owner'][zaehler] != "" :
					contacts_relation_to_owner[contact] = vm['owner'][zaehler]
				zaehler += 1

## @getClientInfo returns a dict  with all infos about a specific saveset
def getClientInfo(saveset,saveTime,backup_state):
	info = {"info" : getBackupLevel(backup_state) + " Saveset: " + saveset + saveTime + " Backup Type: Filesystem"}
	return info

## @getFilesystem_backup_state Fills an array with the last backup states and infos about a node and the filesystem
def getFilesystem_backup_state(vm):
	global filesystems_success, filesystems_failed, debug, baseurl, backup_states
	data=""
	location = ""
	if "location" in vm and vm['location'] != '' and vm['location'] != "" :
		location = locations[vm['location'].lower()] + "_"
	group =  vm['retentionclass']+'_'+vm['clientType']+'_'+location+frequency[vm['frequency'].lower()]+vm['starttime']
	states = requests.request("GET",baseurl+"jobs?fl=command,name,type,clienthostname,completionStatus,message,endTime&q=clienthostname:'"+vm['hostname']+"'" ,data=data,headers=headers,verify=False)
	state = json.loads(states.text)
	backup_states[vm['hostname']] = [[{}]]
	print ("Get Backup State for AGENT: " + vm['hostname'])
	if state['count'] != 0 :
		backup_states[vm['hostname']] = [[{}]] * len(vm['saveSets'])
		for y in range(0,len(vm['saveSets'])):
			savesets_yaml = yaml.load(open(os.getcwd()+"/savesets.yaml",'r'))
			searched_saveset = vm['saveSets'][y]
			for saveset in range(0,len(savesets_yaml['Savesets'])):
				if searched_saveset == savesets_yaml['Savesets'][saveset]['yaml'] :
					searched_saveset = savesets_yaml['Savesets'][saveset]['mapping']
			found = False
			for backup_state in state['jobs'] :
				if "save job" in backup_state['type'] and 'message' in backup_state and 'endTime' in backup_state and backup_state['message'] != "":
					endTimeDate = backup_state['endTime'].split('T')
					endTimeTime = endTimeDate[1].split('+')
					saveTime = " Save Time: " + endTimeTime[0] + " " +endTimeDate[0]
					calctime = datetime.datetime.strptime(endTimeDate[0] +" "+ endTimeTime[0],"%Y-%m-%d %H:%M:%S") +  datetime.timedelta(hours=frequency_to_time[vm['frequency'].lower()])
					calctime_twice = datetime.datetime.strptime(endTimeDate[0] +" "+ endTimeTime[0],"%Y-%m-%d %H:%M:%S") +  datetime.timedelta(hours=frequency_to_time[vm['frequency'].lower()] * 2)
					##For debuging
					if debug.lower() == "true":
						print ("Searching for: " + searched_saveset)
						print ("Job Name: " + backup_state['name'])
						print ("Job message: " + backup_state['message'])
					##
					if searched_saveset == backup_state['name'] and backup_state['type'] == "save job" :
						if calctime > datetime.datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") :
							if backup_state['completionStatus'].lower() == "succeeded":
								filesystems_success += 1
								found = True
								if "error_report" in vm and vm["error_report"].lower() == "true":
									print ("Found a backup which was successfull but won't get displayed due to error_report = true")
									backup_states[vm['hostname']][y] = [{}]
									print ("Found a backup execute break now")
									break;
								else:
									backup_states[vm['hostname']][y] = [{}] * 3
									backup_states[vm['hostname']][y][0] = getClientInfo(vm['saveSets'][y],saveTime,backup_state)
									backup_states[vm['hostname']][y][1] = { 'state' : '' + backup_state['completionStatus']}
									backup_states[vm['hostname']][y][2] = {"Group" : group}
									print ("Found a backup execute break now")
									break;
							else:
								backup_states[vm['hostname']][y] = [{}] * 3
								filesystems_failed += 1
								found = True
								backup_states[vm['hostname']][y][0] = {"info" : "Info: " + parse_networker_message(backup_state['message']) + " Saveset: " + vm["saveSets"][y] + " " + saveTime + " Backup Type: Filesystem"  }
								backup_states[vm['hostname']][y][1] = { 'state' : '' + backup_state['completionStatus']}
								backup_states[vm['hostname']][y][2] = {"Group" : group}
								print ("Found a backup execute break now")
								break;
						elif calctime_twice < datetime.datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") and len(backup_states[vm['hostname']][y]) != 4 :
							backup_states[vm['hostname']][y] = [{}] * 3
							backup_states[vm['hostname']][y][0] = {"info" : "WARNING: No Backup could be Found in the last two frequency periods for Saveset: " + vm["saveSets"][y]}
							backup_states[vm['hostname']][y][1] = {"state" : "Important Warning"}
							backup_states[vm['hostname']][y][2] = {"Group" : group}
						elif calctime_twice > datetime.datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") and len(backup_states[vm['hostname']][y]) != 4 :
							backup_states[vm['hostname']][y] = [{}] * 4
							backup_states[vm['hostname']][y][0] = {"info" : "WARNING: No Backup could be Found in the last frequency period for Saveset: " + vm["saveSets"][y] + "; Last Backup is from " + backup_state['endTime'] + " and had the State: " + backup_state['completionStatus']  }
							backup_states[vm['hostname']][y][1] = {"state" : "Nothing Found"}
							backup_states[vm['hostname']][y][2] = {"Group" : group}
							backup_states[vm['hostname']][y][3] = {"OldBackup" : calctime_twice}
							print ("Found a backup execute break now")
							break;
           
				elif "save job" in backup_state['type'] :
					if 'message' not in backup_state :
						backup_states[vm['hostname']][y] = [{}] * 3
						backup_states[vm['hostname']][y][0] = {"info" : "WARNING: No message found please check backup state maybe Hostname Resolution failed Backup Type: Filesystem"}
						backup_states[vm['hostname']][y][1] = {"state" : "Failed"}
						backup_states[vm['hostname']][y][2] = {"Group" : group}
					elif "save job" in backup_state['type'] :
						backup_states[vm['hostname']][y] = [{}] * 3
						backup_states[vm['hostname']][y][0] = {"info" : parse_networker_message(backup_state['message']) +" Backup Type: Filesystem"}
						if 'completionStatus' in backup_state :
							backup_states[vm['hostname']][y][1] = {"state" : backup_state['completionStatus']}
						else:
							backup_states[vm['hostname']][y][1] = {"state" : "Not known"}
							backup_states[vm['hostname']][y][2] = {"Group" : group}
		if found != True:
			filesystems_failed += 1
	else:
		filesystems_failed += 1
		backup_states[vm['hostname']][0] = [{}] * 3
		backup_states[vm['hostname']][0][0] = {"info" : "WARNING: Seems like their never been an backup Backup Type: Filesystem" }
		backup_states[vm['hostname']][0][1] = {"state" : "WARNING"}
		backup_states[vm['hostname']][0][2] = {"Group" : group}
		return

## @getVM_backup_state Fills the array backup_states with the last backup state and info of a VM
def getVM_backup_state(vm) :
	global vms_success, vms_failed, baseurl
	try:
		location = ""
		if "location" in vm and vm['location'] != '' and vm['location'] != "" :
 			location = locations[vm['location'].lower()] + "_"
		group =  vm['retentionclass']+'_'+vm['backupType']+'_'+location+frequency[vm['frequency'].lower()]+vm['starttime']
		data=""
		states = requests.request("GET",baseurl+"jobs?fl=type,clienthostname,completionStatus,message,endTime&q=clienthostname:'"+vm['hostname']+"'" ,data=data,headers=headers,verify=False)
		state = json.loads(states.text)
		backup_states[vm['hostname']] = [[{}]]
		print ("Get Backup State for VM: " + vm['hostname'])
		if state['count'] != 0 :
			for backup_state in state['jobs'] :
				if 'endTime' in backup_state :
					endTimeDate = backup_state['endTime'].split('T')
					endTimeTime = endTimeDate[1].split('+')
					saveTime = " Save Time: " + endTimeTime[0] + " " +endTimeDate[0]
					if "message" in backup_state:
						calctime = datetime.datetime.strptime(endTimeDate[0] +" "+ endTimeTime[0],"%Y-%m-%d %H:%M:%S") +  datetime.timedelta(hours=frequency_to_time[vm['frequency'].lower()])
						calctime_twice = datetime.datetime.strptime(endTimeDate[0] +" "+ endTimeTime[0],"%Y-%m-%d %H:%M:%S") +  datetime.timedelta(hours=frequency_to_time[vm['frequency'].lower()] * 2)
						if calctime > datetime.datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") :
							##For debuging
							print ("\n Job message: " + backup_state['message'] + " \n")
							##
							if "error_report" in vm and vm["error_report"].lower() == "true" and backup_state['completionStatus'] != "Succeeded":
								vms_failed += 1
								backup_states[vm['hostname']][0][0] = {"info" : saveTime + " Backup Type: VM" }
								backup_states[vm['hostname']][0].append({"state" : "" + backup_state['completionStatus']})
								backup_states[vm['hostname']][0].append({"Group" : group})
								return
							elif "error_report" not in vm or vm["error_report"].lower() == "false":
								if backup_state['completionStatus'] != "Succeeded":
									vms_failed += 1
								else:
									vms_success += 1
								backup_states[vm['hostname']][0][0] = {"info" : saveTime + " Backup Type: VM" }
								backup_states[vm['hostname']][0].append({"state" : "" + backup_state['completionStatus']})
								backup_states[vm['hostname']][0].append({"Group" : group})
								return
							elif "error_report" in vm and vm["error_report"].lower() == "true" and backup_state['completionStatus']:
								if backup_state['completionStatus'] != "Succeeded":
									vms_failed += 1
									backup_states[vm['hostname']][0] = [{}] * 3
									backup_states[vm['hostname']][0][0] = {"info" : saveTime + " Backup Type: VN "}
									backup_states[vm['hostname']][0][1] = {"state" : backup_state['completionStatus']}
									backup_states[vm['hostname']][0][2] = {"Group" : group}
								else:
									print ("Found a backup which was successfull but won't get displayed due to error_report = true")
									vms_success += 1
								return
							else :
								print ("Why am I Here Failed " + vm['hostname'])
								vms_failed += 1
								return
						elif backup_state['type'] == "save job" and calctime_twice < datetime.datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") and len(backup_states[vm['hostname']][0]) != 4:
							backup_states[vm['hostname']][0] = [{}] * 4
							backup_states[vm['hostname']][0][0] = {"info" : "WARNING: No Backup could be Found in the last two frequency periods for VM "}
							backup_states[vm['hostname']][0][1] = {"state" : "Important Warning"}
							backup_states[vm['hostname']][0][2] = {"Group" : group}
						elif len(backup_states[vm['hostname']][0]) != 4:
							backup_states[vm['hostname']][0] = [{}] * 4
							backup_states[vm['hostname']][0][0] = {"info" : "WARNING: No Backup could be Found in the last frequency period for VM" +"; Last Backup is from " + backup_state['endTime'] + " and had the State: " + backup_state['completionStatus']  }
							backup_states[vm['hostname']][0][1] = {"state" : "Nothing Found"}
							backup_states[vm['hostname']][0][2] = {"Group" : group}
							backup_states[vm['hostname']][0][3] = {"OldBackup" : calctime_twice}
						else:
							backup_states[vm['hostname']][0] = [{}] * 3
							backup_states[vm['hostname']][0][0] = {"info" : "The Backup has no Message counting as Failed"}
							backup_states[vm['hostname']][0][1] = {"state" : "Failed. State from networker: " + (backup_state['completionStatus'] if "completionStatus" in backup_state else "None")  }
							backup_states[vm['hostname']][0][2] = {"Group" : group}
							print ("Backup Failed " + vm['hostname'])
			print ("Backup Failed " + vm['hostname'])
			vms_failed += 1
			print ("Failed " + vm['hostname'])
		else:
			vms_failed += 1
			backup_states[vm['hostname']][0][0] = {"info" : "WARNING: Seems like their never been an backup Backup Type: VM"}
			backup_states[vm['hostname']][0].append({"state" : "WARNING"})
			backup_states[vm['hostname']][0].append({"Group" : group})
			return
	except:
		backup_states[vm['hostname']] = [[{}]]
		backup_states[vm['hostname']][0][0] = {"info" : "Exception were thrown. Backup Type: VM"}
		backup_states[vm['hostname']][0].append({"state" : "Exception in script"})
		emailer.send_error_mail(str(traceback.format_exc()))

## @send_metrics_to_graphite create metric for graphite
def send_metrics_to_graphite():
	global vms_success,vms_failed,filesystems_failed,filesystems_success,send_graphiteMetrics, graphite_server, graphite_port, graphite_baseurl
	if send_graphiteMetrics == "true":
		graphite_port = int(graphite_port)
		timestamp = int(time.mktime(now.timetuple()) + now.microsecond / 1E6)
		print ("-------------------------Metrics--------------------------")
		try:
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(10)
			s.sendall((graphite_baseurl+".vms.success " + str(vms_success) +" "+ str(timestamp) + "\n").encode())
			s.close()
			print(graphite_baseurl+".vms.success " + str(vms_success) +" "+ str(timestamp))
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(10)
			s.sendall((graphite_baseurl+".vms.failed " + str(vms_failed) + " " +str(timestamp) + "\n").encode())
			s.close()
			print(graphite_baseurl+".vms.failed " + str(vms_failed) +" "+ str(timestamp))
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(10)
			s.sendall((graphite_baseurl+".client.success " + str(filesystems_success) +" "+ str(timestamp) + "\n").encode())
			s.close()
			print(graphite_baseurl+".client.success " + str(filesystems_success) +" "+ str(timestamp))
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(10)
			s.sendall((graphite_baseurl+".client.failed " + str(filesystems_failed) + " " + str(timestamp) + "\n").encode())
			s.close()
			print(graphite_baseurl+".client.failed " + str(filesystems_failed) +" "+ str(timestamp))
		except:
			emailer.send_error_mail(str(traceback.format_exc()))


## @parse_netweokrer_message returns the relevant information out of the message
def parse_networker_message(message):
	print ("parsing started")
	messages_yaml = yaml.load(open(os.getcwd()+"/messages.yaml",'r'))
	if messages_yaml != None :
		for message_counter in range(0,len(messages_yaml['Messages'])) :
			if message == "" or message == " ":
				return "Nothing Found";
			elif messages_yaml['Messages'][message_counter]['message'] in message:
				splitted_message = message.split(messages_yaml['Messages'][message_counter]['message'])
				return messages_yaml['Messages'][message_counter]['message'] +" "+ splitted_message[1]
		emailer.send_error_mail('Unhandled message please extend script:' + message)
		return message

## @is_networker_available checks if a networker connection can be established
def is_networker_available():
	global baseurl
	result = requests.request("GET",baseurl ,headers=headers,verify=False)
	if result.status_code > 226 :
		return False
	return True

## @getBackupLevel retruns the used backuplevel
def getBackupLevel(backup) :
	if backup['name'] == "pseudo_saveset" :
		message = backup['message'].split('DISASTER_RECOVERY')[1]
		if "full" in message :
			return "Backuplevel: full "
		if "incr" in message :
			return "Backuplevel: incr "

	if "command" in backup:
		if "level=" in backup['message'] :
			return "Backuplevel: " + backup['message'].split('level=')[1].split(',')[0] + " "
		elif "full" in backup["command"] :
			return "Backuplevel: full "
		elif "incr" in backup["command"] :
			return "Backuplevel: incr "
	return "Backuplevel could not be retrieved. "

## @buildFrequencyMapping
def buildFrequencyMapping():
	global frequency,config
	for freq in yaml.load(open(os.getcwd()+"/"+config['files']['basedir']+config['files']['frequencyFile'],'r'))['frequencys']:
		frequency[freq['name']] = freq['value']
	print(frequency)

## @buildLocationMapping
def buildLocationMapping():
	global locations,config
	for loc in yaml.load(open(os.getcwd()+"/"+config['files']['basedir']+config['files']['locations'],'r'))['locations']:
		locations[loc['name']] = loc['value']

## @buildFrequencyToTimeMapping
def buildFrequencyToTimeMapping():
	global frequency_to_time,config
	for freqtt in yaml.load(open(os.getcwd()+"/"+config['files']['basedir']+config['files']['frequencyToTime'],'r'))['toTime']:
		frequency_to_time[freqtt['name']] = freqtt['value']

## @isInIgnoreList
def isInIgnoreList(directory):
	global ignore_directories
	for ignoredDirectory in ignore_directories.split(',') :
		if ignoredDirectory in directory :
			return True
	return False

## @getServerProtectionReport gets all backup states from the machines configured in the server potection group
def getServerProtectionReport():
	global policies, backup_states
	link = baseurl+"protectionpolicies"
	newPolicie = policie.Policie("Server Protection",link,headers)
	newPolicie.getWorkflows()
	newPolicie.getPolicieState()
	backup_states['Server Protection'] = [[{}]]
	if newPolicie.policieState:
		backup_states['Server Protection'][0][0] = {"info":"Policie and workflows were successfull, nothing to worry"}
		backup_states['Server Protection'][0].append({"state" : "Successfull"})
	else:
		backup_states['Server Protection'][0][0] = {"info":"Alert: Policie execution had an error, use the networker gui and fix the error"}
		backup_states['Server Protection'][0].append({"state" : "Error" })
	backup_states['Server Protection'][0].append({"Group":" None (Policie)"})

main() ## Runs the main Method
