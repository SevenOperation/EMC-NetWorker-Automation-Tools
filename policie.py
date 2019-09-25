import workflow
import json
import requests

class Policie():
	policieName = ""
	baseurl = ""
	workflows = []
	headers = ""
	policieState = False
	
	def __init__(self,policieName,baseurl,headers):
		self.policieName = policieName
		self.baseurl = baseurl + "/"+policieName
		self.headers = headers
		self.workflows = []

	def getWorkflows(self):
		print("   --- Trying to get the workflows for " + self.policieName + " ---")
		link = self.baseurl+"/workflows/"
		req = requests.request('GET',link,headers=self.headers,verify=False,timeout=50)
		workflowsJson = json.loads(req.text)['workflows']
		for workflowJson in workflowsJson:
				newWorkflow = workflow.Workflow(link,self.headers,workflowJson['name'])
				newWorkflow.getWorkflowStatus()
				self.workflows.append(newWorkflow)
		print ("  --- Getting workflows end --- \n")
	
	def getPolicieState(self):
		print("--- Trying to get the policie state of "+ self.policieName + " ---")
		for workflowV in self.workflows :
			if workflowV.overallState != "Succeeded":
				print ("   State of Policie " + self.policieName + " is: Failed")
				print ("   End of getting policie state")
				return
		print ("   State of Policie " + self.policieName + " is: Succeeded")
		print ("   End of getting policie state\n")
		self.policieState = "Succeeded"

