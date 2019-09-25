from requests import Request , Session
import requests
import json


class VirtualMachine():
	config = ""
	headers = ""
	baseurl = ""
	mailer = ""
	protectiongroups  = ""
	
	## @__init__ full parameterised constructor
	def __init__(self,config,baseurl,headers,mailer,protectiongroups):
		self.config = config
		self.headers = headers
		self.baseurl = baseurl
		self.mailer = mailer
		self.protectiongroups = protectiongroups

	## @addVM Adds a vm to specific group
	def addVM(self,vm_uuid,vm_group,vCenter,vm) :
		data='{"addWorkItems":{ "vCenterHostname":"'+vCenter+'","vmUuids":["'+vm_uuid+'"]} }'
		print("Trying to add VM:" + vm_uuid + " to the Group: " +vm_group)
		r = requests.request(self.config['vm']['add']['method'],self.baseurl+self.config['vm']['add']['path']+ vm_group +"/"+ self.config['vm']['add']['path2'] ,data=data,headers=self.headers,verify=False)
		if r.status_code > 226 :
			print ("Warning something went wrong ")
			print (r.status_code)
			print (r.text)
			print('--- Virtual Machine end ---\n')
			self.mailer.send_syntax_error_mail(vm,r.text +" "+vm['hostname']+" "+vm_group)
		else:
			print("VM was added")
			print('--- Virtual Machine end ---\n')
		return


	## @searchForVM Searches for a specific vm and returns vmcenter hostname and uuid of the vm     
	def searchForVM(self,vm,vm_object,archive) :
		data=''
		r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+'?fl=hostname',data=data,headers=self.headers,verify=False)
		vmCenters = json.loads(r.text)['vCenters']
		print('--- Virtual Machine begin ---')
		print('The following VM Centers will be searched for the VM '+ vm )
		if 'vcenter' in vm and vcenter != "":
			print(" Search in explicit defined vmCenter: " + vm['vmcenter'] + " begins")
			r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+vm['vcenter']+'/vms?fl=hostname,uuid,name',data=data,headers=self.headers,verify=False)
			vms = json.loads(r.text)['vms']
			for x in range(0,len(vms)) :
				if vms[x]['hostname'] == vm or vms[x]['name'] == vm :
					print("  VM was found and has the following uuid: " + vms[x]['uuid'])
					result = {'uuid':vms[x]['uuid'],'vCenter':vm['vcenter']}
					return result
				if archive :
					print ("VM could not be found but should be in Archive \n")
				else:
					print("VM was not found in the specified vcenter now all will be searched")
		for i in range(0,len(vmCenters)) :
			print(" Search in VM Center " + vmCenters[i]['hostname'] + " begins")
			r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+vmCenters[i]['hostname']+'/vms?fl=hostname,uuid,name',data=data,headers=self.headers,verify=False)
			vms = json.loads(r.text)['vms']
			for x in range(0,len(vms)) :
				if vms[x]['hostname'] == vm or vms[x]['name'] == vm :
					print("  VM was found and has the following uuid: " + vms[x]['uuid'])
					result = {'uuid':vms[x]['uuid'],'vCenter':vmCenters[i]['hostname']}
					return result
				if vms[x]['hostname'].lower() == vm.lower() or vms[x]['name'].lower() == vm.lower() :
					self.mailer.send_syntax_error_mail(vm_object,"VM was found but spelling was wrong, please change vm name from "+vm+" to " + vms[x]['name'] + " Warning casesensitiv. The wrong name will result in a wrong backup report")
					print("VM was found but spelling was wrong, please change vm name from " +vm+" to " + vms[x]['name'] + " Warning casesensitiv. The wrong name will result in a wrong backup report")
					return
		if archive :
			print ("VM could not be found but should be in Archive")
			print('--- Virtual Machine end ---\n')
		else:
			print("The VM does not exists")
			print('--- Virtual Machine end ---\n')
			self.mailer.send_syntax_error_mail(vm_object,"VM " + vm + " does not exists")
		return

	##  @isVmAlreadyKnown determines if vm is already registered in the networker and returns a bool based on that
	def isVmAlreadyKnown(self,yamlGroup,vm_uuid):
		vmAlreadyInGroup = False
		print ("Checking if " + vm_uuid+ " is already known")
		for protectionGroup in self.protectiongroups:
			if "vmwareWorkItemSelection" in protectionGroup :
				for protectedvms in protectionGroup['vmwareWorkItemSelection']['vmUuids'] :
					if protectedvms == vm_uuid and yamlGroup == protectionGroup['name'] : #Checks if the group is the vm is in right now is the same as specified in the yaml if not vm will get removed from old group
						print ("VM already in Group")
						vmAlreadyInGroup = True
					elif protectedvms == vm_uuid:
						print ("Remove VM from old Group")
						self.removeVMFromOldGroup(protectionGroup['name'],vm_uuid)
		return vmAlreadyInGroup

	## @removeVMFromOldGroup removes the vm from the old group
	def removeVMFromOldGroup(self,vm_group,vm_uuid) :
    		status = ""
    		data = ""
    		r = requests.request(self.config['vmcenter']['get']['method'],self.baseurl+self.config['vmcenter']['get']['path']+'?fl=hostname',data=data,headers=self.headers,verify=False)
    		vmCenters = json.loads(r.text)['vCenters']
    		for vCenter in vmCenters :
     			data='{"deleteWorkItems":{ "vCenterHostname":"'+vCenter['hostname']+'","vmUuids":["'+vm_uuid+'"]} }'
     			print("Trying to delete VM:" + vm_uuid + " from the Group: " +vm_group)
     			r = requests.request(self.config['vm']['add']['method'],self.baseurl+self.config['vm']['add']['path']+ vm_group +"/"+ self.config['vm']['add']['path2'] ,data=data,headers=self.headers,verify=False)
     			if r.status_code > 226 :
      				print ("Warning something went wrong while trying to delete \n")
      				print (r.status_code)
     			else:
      				print ("VM is deleted\n")
      				return
