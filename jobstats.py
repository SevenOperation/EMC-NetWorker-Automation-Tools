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
import socket
import policie
from mailer import Mailer

config = yaml.load(open("config.yaml",'r'))['Config'] # Loads config.yaml in to a global variable
now = datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d"),"%Y-%m-%d") #Current Time
requests.packages.urllib3.disable_warnings() #dissables unsecure ssl warnings
#Headers stores http headers (for authentication and content type)
headers= {"Content-Type" : "application/json", "Authorization" : "BASIC "+ sys.argv[3]+""} #stores the informations used to communicate with the networker restapi
rest_server = sys.argv[1] #ip or dns from the networkers restapi
server_port = sys.argv[2] #port of the networkers restapi
error_recipient = sys.argv[4] #full mail address which will recieve error mails
proxies={"https":None}
maildomain = sys.argv[5] #stores the domain part of the email address which will be used for sending example: @web.de
error_sender = sys.argv[6] #stores the name part of the email address which will be used for sending error mails example: recover_error
mailserver = sys.argv[7] #stores the mailserver which should be used for sending mails
debug = sys.argv[8].lower() #stores a boolean which determines wether debug output should be shown or not
backup_number = 0 #is used to determine on which postion the backup was found we will use
restoredSize = 0 #stores the actual backup size which will be sended to graphite to display how many data we have restored
baseurl = "https://"+rest_server+":"+server_port+config['networker_urls']['base'] #stores the baseurl for every request against the networker
policies = []
graphite_server = sys.argv[9]
graphite_port = sys.argv[10]
graphite_baseurl = sys.argv[11]
mailer = Mailer(debug,error_recipient,mailserver,error_sender,"",maildomain)

#Main method for handeling backup type selection
def main():
	global cleanup,mailer
	if isNetWorkerReachable(): 
		print ("Skript is starting")
		getPolicies()
		send_metrics_to_graphite()
	else:
		print ("Networker is not reachable")
		mailer.send_error_mail("NetWorker is not reachable")

def getPolicies():
	global policies
	link = baseurl+"protectionpolicies"
	req = requests.request("GET",link,data="",headers=headers,verify=False,timeout=30)
	protectionpolicies = json.loads(req.text)['protectionPolicies']
	for policieJ in protectionpolicies :
		newPolicie = policie.Policie(policieJ['name'],link,headers)
		newPolicie.getWorkflows()
		newPolicie.getPolicieState()
		policies.append(newPolicie)
		newPolicie = None

def checkDate(backup):
	global now
	if "endTime" in backup:
		backup_datetime = backup['endTime'].split('T')
		backup_time = datetime.datetime.strptime(backup_datetime[0],"%Y-%m-%d")
		if backup_time == now:
			return True
	return False

## @isNetWorkerReachable checks if a connection to the Networker can be Established
def isNetWorkerReachable():
	global baseurl, mailer, debug
	try:
		result = requests.request("GET",baseurl,headers=headers,verify=False,timeout=60)
		if result.status_code > 226 :
			print ("NetWorker not reachable")
			return False
		return True
	except:
		print ("Connection to NetWorker failed: " + str(traceback.format_exc()))
		if debug == "true":
			mailer.send_error_mail("Connection to NetWorker failed:" + str(traceback.format_exc()))

## @send_metrics_to_graphite creates metric for graphite
def send_metrics_to_graphite():
	global policies, graphite_server, graphite_port, graphite_baseurl, mailer
	timestamp = int(time.mktime(now.timetuple()) + now.microsecond / 1E6)
	print ("-------------------------Metrics--------------------------")
	try:
		graphite_port = int(graphite_port)
		for pol in policies :
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(10)
			polName = pol.policieName.replace(" ","")
			if pol.policieState == "Succeeded":
				print(pol.policieName +" "+str(1))
				s.sendall((graphite_baseurl+"."+polName+".state " + str(1) +" "+ str(timestamp) + "\n").encode())
			else:
				print(pol.policieName +" "+str(0))
				s.sendall((graphite_baseurl+"."+polName+".state " + str(0) +" "+ str(timestamp) + "\n").encode())
			s.close()
			for w in pol.workflows:
				s = socket.socket()
				s.connect((graphite_server, graphite_port))
				s.settimeout(10)
				if w.overallState == "Succeeded":
					print(w.workflowName +" "+str(1))
					s.sendall((graphite_baseurl+"."+polName+"."+w.workflowName.replace(" ","")+".state " + str(1) +" "+ str(timestamp) + "\n").encode())
				else:
					print(w.workflowName +" "+str(0))
					s.sendall((graphite_baseurl+"."+polName+"."+w.workflowName.replace(" ","")+".state " + str(0) +" "+ str(timestamp) + "\n").encode())
				s.close()
				for j in w.jobs:
					s = socket.socket()
					s.connect((graphite_server, graphite_port))
					s.settimeout(10)
					if w.jobs[j] == "Succeeded":
						print(j.replace(" ","_") +" "+str(1))
						s.sendall((graphite_baseurl+"."+polName+"."+w.workflowName.replace(" ","")+"."+j.replace(" ","_")+".state " + str(1) +" "+ str(timestamp) + "\n").encode())
					else:
						print(j.replace(" ","_") +" "+str(0))
						s.sendall((graphite_baseurl+"."+polName+"."+w.workflowName.replace(" ","")+"."+j.replace(" ","_")+".state " + str(0) +" "+ str(timestamp) + "\n").encode())
					s.close()
	except:
		mailer.send_error_mail(str(traceback.format_exc()))

main() ## Runs the main Method
