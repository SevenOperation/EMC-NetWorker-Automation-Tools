'''
Created on Feb 11, 2019

@author: mfernitz
'''

# -*- coding: utf-8 -*-
import datetime
import json
import random
import requests
import smtplib
import socket
import sys
import time
import traceback
import yaml

config = yaml.load(open("config.yaml", 'r'))['Config']  # Loads config.yaml in to a global variable
now = datetime.datetime.now()  # Current Time
backup_states = {}  # To store the data "state" and "info" about a backup process
requests.packages.urllib3.disable_warnings()  # dissables unsecure ssl warnings
# Headers stores http headers (for authentication and content type)
headers = {"Content-Type" : "application/json", "Authorization" : "BASIC " + sys.argv[3] + ""}  # stores the informations used to communicate with the networker restapi
modes = {'datadomain':'backup', 'cloud':'s3 clone', 'remote_datadomain':'datadomain clone'}  # Used to map mode parameter to networker backup naming
modes_reversed = {'backup':'datadomain', 's3 clone':'cloud', 'datadomain clone':'remote_datadomain'} 
rest_server = sys.argv[1]  # ip or dns from the networkers restapi
server_port = sys.argv[2]  # port of the networkers restapi
error_recipient = sys.argv[5]  # full mail address which will recieve error mails
recover = sys.argv[4]  # stores a ',' seperated string list with vm names that should be used for recover tests
cleanup = sys.argv[6].lower()  # stores a string which represents a boolean to decide wether the restored vm should be removed afterwards or not
mode = sys.argv[7]  # stores a string which will be used to decide from where the backup should be retrieved
oldest = sys.argv[8]  # stores an boolean to decide wether the oldest backup or the backup from x days before should be used
proxies = {"https":None,"http":None}
backup_from_days_before = int(sys.argv[9])  # stores an int which determines which backup should be restored
maxBackupSize = int(sys.argv[10])  # stores an int which determines how big the backup is allowed to be (in GB)
maildomain = sys.argv[11]  # stores the domain part of the email address which will be used for sending example: @web.de
error_sender = sys.argv[12]  # stores the name part of the email address which will be used for sending error mails example: recover_error
mailserver = sys.argv[13]  # stores the mailserver which should be used for sending mails
debug = sys.argv[14].lower()  # stores a boolean which determines wether debug output should be shown or not
backup_number = 0  # is used to determine on which postion the backup was found we will use
restoredSize = 0  # stores the actual backup size which will be sended to graphite to display how many data we have restored
recoverTarget = sys.argv[16]
recoverTargetPort = sys.argv[17]
recoverurl = "http://" + recoverTarget + ":" + recoverTargetPort   # stores the baseurl for every request against the networker
baseurl = "https://" + rest_server + ":" + server_port + config['networker_urls']['base']  # stores the baseurl for every request against the networker
harddrive = sys.argv[18]
requestTimeout = int(sys.argv[19]) * 60
restoreFilesystem = ""
send_graphiteMetrics = sys.argv[15].lower()  # stores an boolean to decide wether the graphite metrics should be send or not
backupNotFoundMessage = "ERROR No backup found for that Date"
hostId = None


# Main method for handeling backup type selection
def main():
    global recover, cleanup, mode, modes, hostId, restoreFilesystem
    try:
        if isNetWorkerReachable():
            print ("Skript is starting")
            if mode in modes:
                print ("The recover mode is: " + mode)
                mode = modes[mode]
                if cleanup == 'true':
                    cleanup = True
                else:
                    cleanup = False
            clients = json.loads(recover)
            client_number = random.randint(0, len(clients) - 1)
            client = list(clients[client_number].keys())
            print (client)
            client = client[0]
            if len(clients[client_number][client]) >= 1 :
                restoreFilesystem = clients[client_number][client][random.randint(0, len(clients[client_number][client]) - 1)]
            else:
                restoreFilesystem = clients[client_number][client][0]
            print("Saveset " + restoreFilesystem + " was chosen for restore")
            print(client)
            if isBackupBlockBased(client) != False:
                print ("Agent has block based backup enabled")
                result = getBackup(hostId)
                if result !=  None and result != False and checkBackupSize(result):
                    if startRecover(result) and cleanup:
                        cleanupRecoveredData()
                else:
                    send_error_mail("ERROR No Backup found for that date")
                return
            else:
                send_metrics_to_graphite(0)
                send_error_mail("NetWorker is not reachable")
                print ("ERROR Networker is not reachable")
    except:
        send_metrics_to_graphite(0)
        send_error_mail(str(traceback.format_exc()))


## @send_error_mail Sends a mail if an error occur to the mail defined in teamcity as error_mail
def send_error_mail(error) :
    global error_sender, maildomain, error_recipient, mailserver, debug
    try:
        sender = error_sender + maildomain
        server = smtplib.SMTP(mailserver, 25, "mail_domain", 60)
        if debug == "true":
            server.set_debuglevel(1)
        data = "subject: Error \n\n" + " Fehler in backup-recover-test \n Fehlermeldung: " + error 
        server.sendmail(sender, error_recipient, data)
        server.quit()
    except:
        print ("WARNING: WARNING mail could not be send" + error)
        print ("Fehler 2: " + str(traceback.format_exc()))
        return


# # @isBackupBlockedBased
def isBackupBlockBased(hostname):
    global baseurl, hostId
    result = requests.request("GET", baseurl + "clients", headers=headers, verify=False)
    clients = json.loads(result.text)['clients']
    for client in clients:
        if client['hostname'] == hostname and client['blockBasedBackup']:
            hostId = client['resourceId']['id']
            return True
    send_error_mail("Agent doesn't have block based backup enabled")
    send_metrics_to_graphite(0)
    print("ERROR Agent doesn't have block based backup enabled")
    return False


## @getBackup
def getBackup(host_id):
    global baseurl, oldest, mode,restoreFilesystem
    backupData = None
    result = requests.request("GET", baseurl + "clients/" + host_id + "/backups", headers=headers, verify=False)
    backups = json.loads(result.text)['backups']
    if oldest.lower() == "false":
        restore_backup_from_time = datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d") - datetime.timedelta(days=backup_from_days_before)
        backup_number = 0
        for backup in backups:
            oldest_time = backup['completionTime'].split('T')
            backup_time = datetime.datetime.strptime(oldest_time[0], "%Y-%m-%d")
            print ("Restore backup from: " + str(restore_backup_from_time))
            print ("Found backup from: " + str(backup_time))
            print ("With saveset: "+ backup['name'])
            backup_number += 1
            if backup_time == restore_backup_from_time and "DISASTER" not in backup['name'] and restoreFilesystem in backup['name']:
                return backup
        send_metrics_to_graphite(0)
        return False
    else:
        print ("Found a backup")
        print ("using oldest Backup in mode " + str(mode))
        backupData = backups[len(backups) - 1]
        send_metrics_to_graphite(0)
    return backupData


# # @checkBackupSize checks if the backupsize is not bigger then specified
def checkBackupSize(backupData):
    global maxBackupSize, backup_from_days_before , oldest , backup_number, mode, restoredSize, backupNotFoundMessage
    print ("Backup found let's see if it is not to big")
    correct = False
    if backupData['size']['value'] / 1000000000 <= maxBackupSize :
        print ("Backup size is ok") 
        correct = True
        restoredSize = backupData['size']['value'] / 1000000000
    else:
        send_metrics_to_graphite(0)
        backupNotFoundMessage = "ERROR Found a backup from that date but it is exceeding the allowed backup size for the restore test. Allowed are " + str(maxBackupSize) + "GB but found one with " + str(backupData['size']['value'] / 1000000000) + "GB"
        send_error_mail("ERROR Found a backup from that date but it is exceeding the allowed backup size for the restore test. Allowed are " + str(maxBackupSize) + "GB but found one with " + str(backupData['size']['value'] / 1000000000) + "GB")
        print ("ERROR Backup size is to big. Allowed: " + str(maxBackupSize) + "GB Found: " + str(backupData['size']['value'] / 1000000000) + "GB")
    return correct


# #@startRecover
def startRecover(backup):
    global mode,harddrive,proxies,requestTimeout
    for info in backup['attributes'] :
        if info['key'] == "*policy action name":
            available_modes = {}
            for value in info['values']:
                available_modes[value.split(':')[0]]=value.split(':')[1]
            if mode in available_modes :
                mode_id = available_modes[mode]
            else:
                send_error_mail("Mode "+modes_reversed[mode]+" can not be used because there is no backup available from this source, switching to " + modes_reversed[available_modes.keys()[len(available_modes.keys())-1]])
                mode_id = available_modes[available_modes.keys()[len(available_modes.keys())-1]]
            if " " in mode_id:
                mode_id = mode_id.split(' ')[1]
            found_id = True
    if mode_id == "" or mode_id == " ":
        found_id = False
    if found_id == False: #sometimes the networker does not return policy action names if thats the case this handels our fallback and switches to a other backup source 
        if mode == 'datadomain clone' and len(backup['instances']) >=2:
            for b in backup['instances']:
                if b['clone'] == 'true':
                    mode_id = b['id']
        else:
            mode_id = backup['instances'][0]['id']
            send_error_mail("Mode "+modes_reversed[mode]+" can not be used because there is no backup available from this source, switching to datadomain")
            mode = "datadomain"
    global recoverurl
    print (recoverurl)
    try:
        print(recoverurl + "/restoreClient/" + "?ssid=" + backup['shortId'] + "&cloneid=" + mode_id + "&harddrive=" + harddrive+":")
        result = requests.request("GET", recoverurl + "/restoreClient/" + "?ssid=" + backup['shortId'] + "&cloneid=" + mode_id + "&harddrive=" + harddrive+":",proxies=proxies,timeout=requestTimeout)
        print(result.status_code)
        if result.status_code > 226:
            send_error_mail(result.text)
            print("ERROR Something went wrong while recovering" + result.text)
            return False
        print (result.text)
        send_metrics_to_graphite(1)
        return True
    except:
        send_error_mail("While trying to start recover an error occured" + traceback.format_exc())
        print("ERROR While trying to start recover an error occured" + traceback.format_exc())
        return False
    return True
    print(result.text)


# # @isNetWorkerReachable checks if a connection to the Networker can be Established
def isNetWorkerReachable():
    global baseurl
    try:
        result = requests.request("GET", baseurl, headers=headers, verify=False)
        if result.status_code > 226 :
            print ("NetWorker not reachable")
            return False
        return True
    except:
        send_metrics_to_graphite(0)
        send_error_mail("Connection to NetWorker failed:" + str(traceback.format_exc()))
        print ("ERROR Connection to NetWorker failed: " + str(traceback.format_exc()))


# # @send_metrics_to_graphite creates metric for graphite
def send_metrics_to_graphite(success):
    global restoredSize, send_graphiteMetrics
    if send_graphiteMetrics == "true":
        graphite_server = "progrp.rz.is"
        graphite_port = 2003
        timestamp = int(time.mktime(now.timetuple()) + now.microsecond / 1E6)
        print ("-------------------------Metrics--------------------------")
        try:
            s = socket.socket()
            s.connect((graphite_server, graphite_port))
            s.settimeout(10)
            s.sendall("backup.networker.bbb.restored " + str(success) + " " + str(timestamp) + "\n")
            s.close()
            if success == 1:
                s = socket.socket()
                s.connect((graphite_server, graphite_port))
                s.settimeout(10)
                s.sendall("backup.networker.bbb.restoredSize " + str(restoredSize) + " " + str(timestamp) + "\n")
                s.close()
        except:
            send_error_mail(str(traceback.format_exc()))

def cleanupRecoveredData():
    global harddrive,requestTimeout
    time.sleep(20)
    result = requests.request("GET", recoverurl + "/cleanup/?harddrive="+harddrive,proxies=proxies,timeout=requestTimeout)
    if result.status_code > 226 :
            send_error_mail("ERROR Something went wrong while cleanup "+ result.text)
            print ("ERROR Something went wrong while cleanup")
    print(result.text)
    

  
main()  # # Runs the main Method
