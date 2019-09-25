from requests import Request , Session
import requests
import json
import re



class Agent():
	headers = ""
	baseurl = ""
	config = ""
	requests.packages.urllib3.disable_warnings()

	def __init__(self,baseurl,headers,config):
		self.headers = headers
		self.config = config
		self.baseurl = baseurl

	## @deleteClient Deletes a vm from specific group
	def deleteClient(self,clientID) :
    		print("Trying to delete agent: " + clientID)
    		r = requests.request('DELETE',self.baseurl+self.config['update']['path']+clientID ,headers=self.headers,verify=False)
    		if r.status_code != 204 :
     			print ("Warning something went wrong while trying to delete \n")
     			print (r.status_code)
    		else:
     			print ("agent got deleted\n")
    		return

	## @getClient returns client infos from networker
	def getClient (self,hostname) :
    		data = ""
    		r = requests.request(self.config['get']['method'],self.baseurl+self.config['get']['path']+'?q=hostname:"'+hostname+'"',data=data,verify=False,headers=self.headers)
    		knownClient = json.loads(r.text)['clients']
    		return knownClient


