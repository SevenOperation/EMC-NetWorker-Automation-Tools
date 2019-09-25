from requests import Request , Session
import requests
import json
import re

class VMuuid():

	headers= ""
	config = ""
	baseurl = ""
	requests.packages.urllib3.disable_warnings()
	
	def __init__(self,headers,baseurl,config):
		self.headers = headers
		self.config = config
		self.baseurl = baseurl

	## @deleteVM Deletes a vm from specific group
	def deleteVM(self,vm_uuid,vm_group) :
		status = ""
		data = ""
		r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+'?fl=hostname',data=data,headers=self.headers,verify=False)
		vmCenters = json.loads(r.text)['vCenters'] 
		for vCenter in vmCenters :
			data='{"deleteWorkItems":{ "vCenterHostname":"'+vCenter['hostname']+'","vmUuids":["'+vm_uuid+'"]} }'
			print("Trying to delete VM:" + vm_uuid + " from the Group: " + vm_group)
			r = requests.request(self.config['vm']['add']['method'],self.baseurl+self.config['vm']['add']['path']+ vm_group +"/"+ self.config['vm']['add']['path2'] ,data=data,headers=self.headers,verify=False)
			if r.status_code > 226 :
				print("Warning something went wrong while trying to delete \n")
				print(r.status_code)
			else:
				print("VM is deleted\n")
				return

