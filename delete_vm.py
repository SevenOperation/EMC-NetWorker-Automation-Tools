from requests import Request , Session
import requests
import json
import re

class VM():
	headers = ""
	config = ""
	baseurl = ""
	requests.packages.urllib3.disable_warnings()
		
	def __init__(self,headers,baseurl,config):
		self.headers = headers
		self.config = config
		self.baseurl=baseurl

	## @deleteVM Deletes a vm from specific group
	def deleteVM(self,vm_uuid,vm_group,vCenter) :
    		data='{"deleteWorkItems":{ "vCenterHostname":"'+vCenter+'","vmUuids":["'+vm_uuid+'"]} }'
    		print("Trying to delete VM:" + vm_uuid + " from the Group: " +vm_group)
    		r = requests.request(self.config['vm']['add']['method'],self.baseurl+self.config['vm']['add']['path']+ vm_group +"/"+self.config['vm']['add']['path2'] ,data=data,headers=self.headers,verify=False)
    		if r.status_code > 226 :
     			print ("Warning something went wrong while trying to delete \n")
     			print (r.status_code)
    		else:
     			print ("VM is deleted\n")
    		return

	##  @searchForVM Searches for a specific vm and returns vmcenter hostname and uuid of the vm     
	def searchForVM(self,vm) :
    		data=''
    		r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+'?fl=hostname',data=data,headers=self.headers,verify=False)
    		vmCenters = json.loads(r.text)['vCenters']
    		print('The following VM Centers will be searched for the VM '+ vm )
    		for i in range(0,len(vmCenters)) :
     			print(" Search in VM Center " + vmCenters[i]['hostname'] + " begins")
     			r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+vmCenters[i]['hostname']+'/vms?fl=hostname,uuid,name',data=data,headers=self.headers,verify=False)
     			vms = json.loads(r.text)['vms']
     			for x in range(0,len(vms)) :
       				if vms[x]['hostname'] == vm or vms[x]['name'] == vm :
        				print("  VM was found and has the following uuid: " + vms[x]['uuid'])
        				result = {'uuid':vms[x]['uuid'],'vCenter':vmCenters[i]['hostname']}
        				return result
    		print("The VM does not exsits\n")
    		return

