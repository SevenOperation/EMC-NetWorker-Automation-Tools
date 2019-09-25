from requests import Request , Session
import requests
import json
import re
import yaml
import os
import datetime
import sys
import time
import traceback
import client
import virtual_machine
import mailer 

#Loads config in a global variable
config = yaml.load(open("script-config/config.yaml",'r'))['Config']

#Directories that store Data for Frequency and Locations 
frequency = {}
locations = {}

group_node_relation = {}

#Headers stores http headers (for authentication and content type)
headers= {"Content-Type" : "application/json", "Authorization" : 'BASIC '+sys.argv[3]}
server = sys.argv[1] #dns or ip of the networker
server_port = sys.argv[2] #server port from the networker
ignored_directories = sys.argv[4] #directories which will be ignored
error_recipient = sys.argv[5]  #recipient for error mails
send_syntax_errors = sys.argv[6] #boolean if syntax errors should be send to registered vm owner, if debug is true or no owner is sepcified it will be sended to error_recipient
debug = sys.argv[7] #if all mails should be send to error_recipeint because it runs for debug purposes
clientF="" #stores later on an object from class Client which is used to call client specific functions
vmF="" #stores later on an object from class VirtualMachine which is used to call client specific functions
mailerF = "" #stores later on an object from class Mailer which is used to send error and report mails
send_group_relation_report = sys.argv[8] #is a string which represents a boolean and decides if a relation report will be sended
error_sender = sys.argv[9] #inherits the mail address of the sender in case for an error example: "abcd" the @domain.de is saved in maildomain
report_sender = sys.argv[10] #inherits the mail address of the sender for the report
maildomain = sys.argv[11] #stores the @example.com for the sender addresses
mailserver = sys.argv[12]
baseurl = "https://"+server+":"+server_port+config['networker_urls']['base']
#stores all defined group names
protectiongroups = ""
#Stores already registered clients for faster process
requests.packages.urllib3.disable_warnings()
protectedVMS = 0


#Main method for handeling backup type selection
def main():
	global clientF,vmF,mailerF,protectiongroups,config,group_node_relation,debug,send_group_relation_report,protectedVMS,error_sender,report_sender,maildomain,mailserver,baseurl,send_syntax_errors
	if is_networker_available():
		mailerF = mailer.Mailer(debug,error_recipient,mailserver,error_sender,report_sender,maildomain,"",send_syntax_errors)
		mailerF.config = config
		try:
			buildFrequencyMapping()
			buildLocationMapping()
			clientF = client.Client(locations,frequency,config['networker_urls'],headers,baseurl,mailerF) # Creates an object of the class Client for using all managing functions
			getProtectionGroups()
			vmF = virtual_machine.VirtualMachine(config['networker_urls'],baseurl,headers,mailerF,protectiongroups)# Creates an object of the class Client for using all managing functions
			clientF.getClients()
			for directorie,subdirs,filenames in os.walk(os.getcwd()):
				if isInIgnoreList(directorie) == False : 
					if "archive" not in directorie:
						for filename in filenames:
							if ".yaml" in filename :
								try:
									yamlD = yaml.load(open(directorie+"/"+filename,'r'))
									if yamlD != None and 'Client' in yamlD:
										for x in range(0,len(yamlD['Client'])) :
											try:
												location = ""
												if "location" in yamlD['Client'][x] :
													location = locations[yamlD['Client'][x]['location'].lower()] + "_"
												group=yamlD['Client'][x]['retentionclass']+"_VM_"+location+frequency[yamlD['Client'][x]['frequency'].lower()]+yamlD['Client'][x]['starttime']
												if yamlD['Client'][x]['backupType'] == "VM" :
													protectedVMS += 1 
													result = vmF.searchForVM(yamlD['Client'][x]['hostname'],yamlD['Client'][x],False)
													if result != None:
														if vmF.isVmAlreadyKnown(group, result['uuid']) == False : 
															vmF.addVM(result['uuid'],group,result['vCenter'],yamlD['Client'][x])
															createGroupNode_Assoziation(yamlD['Client'][x],group)
												else:
													if clientF.clientExists(yamlD['Client'][x]) :
														createGroupNode_Assoziation(yamlD['Client'][x],group)
													else :
														print("Node " + yamlD['Client'][x]['hostname'] +" not known, trying to create backup entry")
														clientF.createClient(yamlD['Client'][x])
														createGroupNode_Assoziation(yamlD['Client'][x],group)
											except:
												mailerF.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['Client'][x]['hostname'])
								except:
									mailerF.send_error_mail(str(traceback.format_exc()))
					else:
						doArchive(directorie)
			if send_group_relation_report.lower() == 'true':
				mailerF.send_group_node_relation_mail(group_node_relation)
			print("Number of processed vms: " + str(protectedVMS))
		except:
			print("something went wrong")
			print("sending error message to developer maurice fernitz")
			mailerF.send_error_mail(str(traceback.format_exc()))
	else:
		print("ERROR: please check if the ntworker is available")

## @doArchive does specific actions for the files in the archive directories
def doArchive(directorie):
	global client, mailerF,config
	for filename in os.listdir(directorie):
		for archive in yaml.load(open(config['files']['basedir']+config['files']['archiveDirectories'],'r'))["Directories"]:
			if ".yaml" not in filename and filename in archive['Name']:
				for yamlfile in os.listdir(directorie + "/" + filename):
					try:
						yamlD = yaml.load(open(directorie+"/"+filename+"/"+yamlfile,'r'))
						if yamlD != None :
							for x in range(0,len(yamlD['Client'])) :
								try:
									if yamlD['Client'][x]['backupType'] == "VM" :
										result = vmF.searchForVM(yamlD['Client'][x]['hostname'],yamlD['Client'][x],True)
										group=filename
										createGroupNode_Assoziation(yamlD['Client'][x],group)
										if result != None :
											location = ""
											if "location" in yamlD['Client'][x] :
												location = locations[yamlD['Client'][x]['location'].lower()] + "_"
											if vmF.isVmAlreadyKnown(group, result['uuid']) == False :
												vmF.addVM(result['uuid'],group,result['vCenter'],yamlD['Client'][x])
									else:
											if clientF.clientExists(yamlD['Client'][x]) :
												print("")
											else :
												print("Node " + yamlD['Client'][x]['hostname'] +" not known, trying to create backup entry")
												clientF.createClient(yamlD['Client'][x])
								except:
									mailerF.send_error_mail(str(traceback.format_exc()) + " NODE: " + yamlD['Client'][x]['hostname'])
					except:
						mailerF.send_error_mail(str(traceback.format_exc()))

## @createGroupNode_Assoziation fills the list with vm to group assoziation
def createGroupNode_Assoziation(vm,group):
	if group not in group_node_relation:
		group_node_relation[group] = []
	group_node_relation[group].append(vm['hostname'])

## @is_networker_available checks if connection to the networker can be established
def is_networker_available():
	result = requests.request("GET","https://"+server+":"+server_port+"/nwrestapi/v2/global/" ,headers=headers,verify=False)
	if result.status_code > 226 :
		return False
	return True

## @getProtectionGroups returns a list with all available protectiongroups
def getProtectionGroups():
	global protectiongroups
	protectiongroups = json.loads(requests.request("GET","https://"+server+":"+server_port+"/nwrestapi/v2/global/protectiongroups",headers=headers,verify=False).text)['protectionGroups']

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

## @isInIgnoreList
def isInIgnoreList(directory):
	global ignored_directories
	print(ignored_directories + " " +  directory)
	for ignoredDirectory in ignored_directories.split(',') :
		print(directory + " " + ignoredDirectory)
		if ignoredDirectory in directory :
			return True
	return False

main()
