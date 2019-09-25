import requests
import datetime
import json

class Workflow():
	overallState = False
	workflowName = ""
	baseurl = ""
	headers = ""
	jobs = {}
	now = datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S") #Current Time
		
	def __init__(self,baseurl,headers,workflowName):
		requests.packages.urllib3.disable_warnings()
		self.baseurl = baseurl
		self.headers = headers
		self.workflowName = workflowName
		self.jobs = {}

	def getWorkflowStatus(self):
		print("      Trying to get the wokflow state now for " + self.workflowName)
		req = requests.request('GET',self.baseurl+self.workflowName+"/jobgroups",headers=self.headers,verify=False,timeout=50)
		workflowJobs = json.loads(req.text)['jobs']
		for workflowJob in workflowJobs:
			if "endTime" in workflowJob and self.checkDate(workflowJob['endTime']):
				req = requests.request('GET',self.baseurl+self.workflowName+"/jobgroups/"+str(workflowJob['id']),headers=self.headers,verify=False,timeout=50)
				print("         "+self.baseurl+self.workflowName+"/jobgroups/"+str(workflowJob['id']))
				workflowJobJson = json.loads(req.text)['jobs']
				for w in workflowJobJson:
					if "completionStatus" in w and w['type'] == "workflow job":
						self.overallState = w['completionStatus']
						break
					else:
						self.overallState = "Failed"
				print("        "+self.overallState+"\n")
				self.getJobStates(workflowJobJson,workflowJob['id'])
				return
		print(str(self.overallState)+"")
		return

	def getJobStates(self,workflowJobsJson,jid):
		print("        Trying to get the job states for " + self.workflowName + " now")
		a = True
		for job in workflowJobsJson:
				if job['type'] != "workflow job" and job['parentJobId']==jid :
					if "completionStatus" in job:
						if job['name'] == "savegrp":
							self.jobs[job['type']] = job['completionStatus']
							print("         Job Name:" + job['type'] + " State: "+job['completionStatus'])
						elif job['type'] == "clone job":
							self.jobs[job["command"].split("policy action name=")[1].split('"')[0]] = job['completionStatus']
							print("         Job Name:" + job["command"].split("policy action name=")[1].split('"')[0] + " State: "+job['completionStatus'])
						else:
							self.jobs[job['name']] = job['completionStatus']
							print("         Job Name:" + job['name'] + " State: "+job['completionStatus'])
					else:
						self.jobs[job['name']] = "Failed"
						print("         Job Name:" + job['name'] + " State: Failed")
				elif job['type'] == "save job" and a != False and "AGENT" not in self.workflowName:
					print("         Job Name:" + job['type'] +" State: "+job['completionStatus'])
					self.jobs[job['type']] = job['completionStatus']
					if job['completionStatus'] != "Succeeded":
						a = False
		return

	def checkDate(self,date):
		backup_datetime = date.split('T')
		endTimeTime = backup_datetime[1].split('+')
		end_time = datetime.datetime.strptime(backup_datetime[0] +" "+ endTimeTime[0],"%Y-%m-%d %H:%M:%S") +  datetime.timedelta(hours=24)
		if end_time >= self.now:
			return True
		return False
	
