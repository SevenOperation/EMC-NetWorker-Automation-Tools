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
from collections import OrderedDict
import random
import socket
import ast

config = yaml.load(open("config.yaml",'r'))['Config'] # Loads config.yaml in to a global variable
now = datetime.datetime.now() #Current Time
backup_states = {} # To store the data "state" and "info" about a backup process
requests.packages.urllib3.disable_warnings() #dissables unsecure ssl warnings
#Headers stores http headers (for authentication and content type)
vmWareHeaders = {} #stores the information returned after authenticating against vcenter call the api
vmware_user = sys.argv[3] #stores the vm user used for authenticating agianst the vcenter
vmware_password = sys.argv[4] #stores the vmware password to authenicate agianst the vcenter
error_recipient = sys.argv[1] #full mail address which will recieve error mails
cleanup = sys.argv[2].lower() #stores a string which represents a boolean to decide wether the restored vm should be removed afterwards or not
vcenter = "" #stores the vcenter name on which the vm we want to restore is right now
proxies={"https":None}
maildomain = sys.argv[5] #stores the domain part of the email address which will be used for sending example: @web.de
error_sender = sys.argv[6] #stores the name part of the email address which will be used for sending error mails example: recover_error
mailserver = sys.argv[7] #stores the mailserver which should be used for sending mails
debug = sys.argv[8].lower() #stores a boolean which determines wether debug output should be shown or not
restoredSize = 0 #stores the actual backup size which will be sended to graphite to display how many data we have restored
send_graphiteMetrics = sys.argv[9].lower() #stores an boolean to decide wether the graphite metrics should be send or not
backupNotFoundMessage = "ERROR No backup found for that Date"
vcenter_ip_address = sys.argv[10]
graphite_server = sys.argv[11]
graphite_port = int(sys.argv[12])
graphite_baseurl = sys.argv[13]
vcenter_name = sys.argv[14]
vmname = sys.argv[15] + "_recovered"
vcenter = sys.argv[16]

#Main method for handeling backup type selection
def main():
	global cleanup,mode,modes, vmname
	if isVCenterReachable():
		print ("Skript is starting")
		if cleanup == 'true':
			cleanup = True
		else:
			cleanup = False
		authenticate('<Your location name>')
		vm_id = getVMFromAPI(vmname,'<Your Location name')
		if vm_id == "" :
			print("VM was not found since it should have been found by now script will be stopped and not executed again")
			return
		if cleanup and isPowerOn(vm_id,'<Your location name>') :
			print("Now deleting")
			shutdown(vm_id,'<your location name>')
			delete(vm_id,'<your location name>')
	else:
		print("Networker or VCenter is not reachable")
		send_metrics_to_graphite(0)
		send_error_mail("NetWorker or VCenter is not reachable")

## @send_error_mail Sends a mail if an error occur to the mail defined in teamcity as error_mail
def send_error_mail(error) :
	global error_sender, maildomain,error_recipient,mailserver,debug
	try:
		sender = error_sender + maildomain
		server = smtplib.SMTP(mailserver,25,"mail_domain",60)
		if debug == "true":
			server.set_debuglevel(1)
		data = "subject: Error \n\n" + " Fehler in backup-recover-test \n Fehlermeldung: " + error 
		server.sendmail(sender,error_recipient,data)
		server.quit()
	except:
		print ("WARNING: WARNING mail could not be send" + error)
		print ("Fehler 2: " + str(traceback.format_exc()))
		return

## @authenticate does the authentication process against vcenter
def authenticate(location):
	global vmWareHeaders, vcenter_ip_address, proxies, vmware_user, vmware_password
	print ("Authenticate against Automation Rest api from vcenter")
	print (vcenter_ip_address)
	try:
		req = requests.request('POST','https://'+vcenter+'/rest/com/vmware/cis/session',auth=(vmware_user,vmware_password),proxies=proxies,verify=False)
		vmWareHeaders={'vmware-api-session-id':json.loads(req.text)['value']}
		if req.status_code > 201:
			send_error_mail('Authentication against vcenter failed')
			print ("ERROR Authentication against vcenter failed")
	except:
		send_error_mail('Authentication against vcenter failed: ' + str(traceback.format_exc()) )
         
## @getVMFromAPI getsVM from vcenter
def getVMFromAPI(vm_name, location ):
	global vmWareHeaders, vcenter, proxies
	print ("Search " + vm_name + " in vcenter " + vcenter)
	if location.lower() == '<your location>' :
		found = False
		vm = ""
		req = requests.request('GET','https://'+vcenter+'/rest/vcenter/vm?filter.names.1='+vm_name+'',proxies=proxies,headers=vmWareHeaders,verify=False)
		print (req.text)
		print (req.status_code)
		if req.status_code == 200 and len(json.loads(req.text)['value']) > 0:
			vm = json.loads(req.text)['value'][0]['vm']
			found = True
		else:
			print ("VM was not found")
		return vm

## @isPowerOn checks if the vm is up and running
def isPowerOn(vm_id,location):
	global vmWareHeaders, vcenter, proxies
	print ("Check if VM is already up")
	online = False
	req = requests.request('GET','https://'+vcenter+'/rest/vcenter/vm/'+vm_id,headers=vmWareHeaders,proxies=proxies,verify=False)
	power_state = json.loads(req.text)['value']['power_state']
	print (power_state)
	if power_state == 'POWERED_ON': 
		send_metrics_to_graphite(1)
		online=True
	if online == False :
		#send_error_mail('VM is not powered up after 8h')
		send_metrics_to_graphite(0)
		print ("ERROR: VM is not powered up yet trying again in 10 minutes")
	return online

## @shutdown shuts the vm down
def shutdown(vm,location):
	global vcenter, vmWareHeaders, proxies
	print ("Shutting down recovered VM")
	req = requests.request('POST','https://'+vcenter+'/rest/vcenter/vm/'+vm+'/power/stop',headers=vmWareHeaders,proxies=proxies,verify=False)
	time.sleep(60) 

## @delete deletes the vm
def delete(vm,location):
	global vcenter, vmWareHeaders, proxies
	print ("Starting Cleanup of recovered VM")
	req = requests.request('DELETE','https://'+vcenter+'/rest/vcenter/vm/'+vm,headers=vmWareHeaders,proxies=proxies,verify=False)
	time.sleep(60) 

## @isVCenterReachable checks if a connection to the vcenter can be established
def isVCenterReachable():
	global proxies, vmware_user, vmware_password, vcenter_ip_address
	try:
		req = requests.request('POST','https://'+vcenter_ip_address+'/rest/com/vmware/cis/session',auth=(vmware_user,vmware_password),proxies=proxies,verify=False,timeout=60)
		if req.status_code > 226 :
			print ("VCenter not reachable")
			print (req.text)
			return False
		return True
	except:
		print ("Connection to VCenter failed: " + str(traceback.format_exc()))
		send_error_mail("Connection to VCenter failed:" + str(traceback.format_exc()))


## @send_metrics_to_graphite creates metric for graphite
def send_metrics_to_graphite(success):
	global restoredSize,send_graphiteMetrics, graphite_server, graphite_port, graphite_baseurl
	graphite_port = int(graphite_port)
	if send_graphiteMetrics == "true":
		timestamp = int(time.mktime(now.timetuple()) + now.microsecond / 1E6)
		print ("-------------------------Metrics--------------------------")
		try:
			s = socket.socket()
			s.connect((graphite_server, graphite_port))
			s.settimeout(20)
			s.sendall((graphite_baseurl+".restored " + str(success) +" "+ str(timestamp) + "\n").encode())
			s.close()
			if success == 1:
				s = socket.socket()
				s.connect((graphite_server, graphite_port))
				s.settimeout(10)
				s.sendall((graphite_baseurl+".restoredSize " + str(restoredSize) +" "+ str(timestamp) + "\n").encode())
				s.close()
		except:
			send_error_mail(str(traceback.format_exc()))

main() ## Runs the main Method
