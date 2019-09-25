from requests import Request , Session
import requests
import json


## Class which inherits all actions for client based backups
class Client():
	locations = ""
	frequency = ""
	config = ""
	headers = ""
	requests.packages.urllib3.disable_warnings()
	knownClients = ""
	mailer = ""	
	baseurl = ""

	def __init__(self,locations,frequency,config,headers,baseurl,mailer):
		self.locations = locations
		self.frequency = frequency
		self.config = config
		self.headers = headers
		self.baseurl = baseurl
		self.mailer =  mailer

	##  @createClient is responsible for creating entrys for new clients on the server
	def createClient (self,newClient)  :
		location = ""
		if "location" in newClient and newClient['location'] != '' and newClient['location'] != "" :
			location = self.locations[newClient['location'].lower()] + "_"
		group = newClient['retentionclass']+'_'+newClient['clientType']+'_'+location+self.frequency[newClient['frequency'].lower()]+newClient['starttime']
		if 'parallelSaveStreams' not in newClient:
			newClient['parallelSaveStreams'] = 'false'
		if 'preCommand' not in newClient :
			newClient['preCommand'] = ""
		if 'postCommand' not in newClient :
			newClient['postCommand'] = ""
		if 'blockBasedBackup' not in newClient:
			newClient['blockBasedBackup'] = "false"
		data = {
        		"aliases": newClient['aliases'], 
        		"hostname": newClient['hostname'],
        		"protectionGroups": [group],
        		"scheduledBackup": newClient['scheduledBackup'],
        		"backupType": newClient['backupType'],
        		"parallelism": str(newClient['parallelism']),
        		"saveSets": newClient["saveSets"],
        		"parallelSaveStreamsPerSaveSet": newClient["parallelSaveStreams"].lower(),
        		"preCommand": newClient['preCommand'],
        		"postCommand": newClient['postCommand'],
        		"blockBasedBackup": newClient['blockBasedBackup']
		}
		data = json.dumps(data)
		r = requests.request(self.config['create']['method'],self.baseurl+self.config['create']['path'],data=data,headers=self.headers,verify=False)
		if r.status_code > 226 :
			print("WARNING: " + json.loads(r.text)['message'] )
			self.mailer.send_syntax_error_mail(newClient,json.loads(r.text)['message'])
		else:
			print("Agent "+ newClient['hostname'] +" is created")
			print('--- Agent end ---\n')
		return

	## @updateClient overrides each settings with the new provided one, returns nothing
	def updateClient (self, clientId , newClient) :
		location = ""
		if "location" in newClient :
			location = self.locations[newClient['location'].lower()] + "_"
		group = newClient['retentionclass']+'_'+newClient['clientType']+'_'+location+self.frequency[newClient['frequency'].lower()]+newClient['starttime']
		if 'parallelSaveStreams' not in newClient:
			newClient['parallelSaveStreams'] = 'false'
		if 'preCommand' not in newClient :
			newClient['preCommand'] = ""
		if 'postCommand' not in newClient :
			newClient['postCommand'] = ""
		if 'blockBasedBackup' not in newClient:
			newClient['blockBasedBackup'] = "false"
		data = {
        		"aliases": newClient['aliases'],
        		"hostname": newClient['hostname'],
        		"protectionGroups": [group],
        		"scheduledBackup": newClient['scheduledBackup'],
        		"backupType": newClient['backupType'],
        		"parallelism": str(newClient['parallelism']),
        		"saveSets": newClient["saveSets"],
        		"parallelSaveStreamsPerSaveSet": newClient["parallelSaveStreams"].lower(),
        		"preCommand": newClient['preCommand'],
        		"postCommand": newClient['postCommand'],
        		"blockBasedBackup": newClient['blockBasedBackup']
    			}
		data = json.dumps(data)
		r = requests.request(self.config['update']['method'],self.baseurl+self.config['update']['path']+clientId,data=data,headers=self.headers,verify=False)
		if r.status_code > 226 :
			print("WARNING: " + json.loads(r.text)['message'])
		else:
			print("Agent " + newClient['hostname'] + " was updated" )
			print('--- Agent end ---\n')
		return

	## @getClients returns an array which stores all client infos from which already exists on the server
	def getClients (self) :
    		data = ""
    		r = requests.request(self.config['get']['method'],self.baseurl+self.config['get']['path'],data=data,verify=False,headers=self.headers)
    		self.knownClients = json.loads(r.text)['clients']

	## @clientExists checks if a client with this hostname is alreday known, if so it also calls the update Client function and returns true, otherwise it returns false    
	def clientExists(self,newClient) :
		print('--- Agent begin ---')
		for i in range(0, len(self.knownClients)) :
			if self.knownClients[i]['hostname'] == newClient['hostname'] : #"" will be replaced by newClient
				print("Agent " + self.knownClients[i]['hostname'] + " already exists, agent will be updated")
				self.updateClient(self.knownClients[i]['resourceId']['id'],newClient)
				return True
		return False

