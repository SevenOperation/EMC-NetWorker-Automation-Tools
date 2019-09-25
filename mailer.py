import traceback
from collections import OrderedDict
from email.mime.text import MIMEText
import smtplib
import datetime

class  Mailer():
	error_recipient = ""
	mailserver = ""
	error_sender = ""
	maildomain = ""
	report_sender = ""
	debug = "false"
	admin_report_recipient = ""
	send_syntax_errors = "false"
	config = ""
	now = datetime.datetime.now()
	
	## @__init__ constructor         
	def __init__(self,debug,error_recipient,mailserver,error_sender,report_sender,maildomain,admin_report_recipient="",send_syntax_errors="false"):
		self.debug = debug
		self.error_recipient = error_recipient
		self.mailserver = mailserver
		self.error_sender = error_sender
		self.maildomain = maildomain
		self.report_sender = report_sender
		self.admin_report_recipient = admin_report_recipient
		self.send_syntax_errors = send_syntax_errors

	## @send_error_mail sends an mail with traceback info if an error occurs
	def send_error_mail(self,error) :
		try:
			sender = self.error_sender+self.maildomain
			serverm = smtplib.SMTP(self.mailserver,25,self.maildomain",10)
			serverm.set_debuglevel(1)
			data = "subject: Error \n\n" + " " + error
			serverm.sendmail(sender,self.error_recipient,data)
			serverm.quit()
		except:
			print ("Error: Error mail could not be send " + str(traceback.format_exc()))
		return
	
	## @send_syntax_error_mail sends an error mail to the specified mail address
	def send_syntax_error_mail(self,vm,text):
		if self.send_syntax_errors == "true":
			recipient = ""
			if self.debug.lower() == "false":
				if "email" in vm and len(vm['email']) > 0:
					recipient = vm['email'][0]
				elif "mail" in vm and len(vm['mail']) > 0:
					recipient = vm['mail'][0]
				else:
					print ("No recipient sending error mail to DCI Storage")
					recipient = self.error_recipient
			else:
				recipient = self.error_recipient
			try:
				sender = self.error_sender + self.maildomain
				serverm = smtplib.SMTP(self.mailserver,25,"mail_domain",60)
				if self.debug.lower() == 'true':
					serverm.set_debuglevel(1)
				else :
					print ("\n An Error occured. Errormail will be sended \n")
				data = "subject: Error \n\n" + " " + text
				serverm.sendmail(sender,recipient,data)
				serverm.quit()
			except:
				print ("Error: Error mail could not be send " + str(traceback.format_exc()))
				print (text)
			return


	## @send_admin_report_mail Sends a mail with a list of all not succeeded backups
	def send_admin_report_mail(self,backup_states):
		sender = self.report_sender + self.maildomain
		data = open(self.config['files']['basedir']+self.config['files']['maillayout'],'r')
		server = smtplib.SMTP(self.mailserver,25,"mail_domain",60)
		if self.debug.lower() == "true":
			server.set_debuglevel(1)
		text = "<p style='text-align: center'>Dear Backup Admin, please find your Backup Report from "+self.now.strftime("%d-%m-%Y %H:%M")+"</p>"
		table = "<table border='2' style='width: 90%'>"
		table += "<tr><td>Hostname</td><td>Backup State</td><td>Backup Information</td><td>Backup Group</td></tr>"
		height = 50
		for backup in  backup_states.keys(): 
			not_succeeded = ""
			for key in range(0,len(backup_states[backup])) :
				try:
					if 2<= len(backup_states[backup][key]) and "state" in backup_states[backup][key][1]:
						if backup_states[backup][key][1]["state"] != 'Succeeded':
							if not_succeeded == '': 
								not_succeeded = str(key)
							else:
								not_succeeded += ","+str(key)
				except:
					self.send_error_mail(str(traceback.format_exc()) + " VM: " + backup) 
			if not_succeeded != '':
				table += "<tr><td>" +backup + "</td><td><table>"
				for key in not_succeeded.split(',') :
					if 1 < len(backup_states[backup][int(key)]) :
						table += "<tr><td>" + backup_states[backup][int(key)][1]['state']+"</td></tr>"
						height += 32
				table += "</table></td><td><table>"
				for key in not_succeeded.split(',') :
					if 'info' in backup_states[backup][int(key)][0] :
						table += "<tr><td>"+backup_states[backup][int(key)][0]['info']+"</td></tr>"
				table+= "</table></td>"
				table += "<td><table>"
				for key in not_succeeded.split(',') :
					if 'Group' in backup_states[backup][int(key)][2] :
						table += "<tr><td>"+backup_states[backup][int(key)][2]['Group']+"</td></tr>"
				table+= "</table></td></tr>"
		table += "</table></div>"
		text += table
		if height < 1100 :
			height = 1100
		html = data.read() + "<div style='width: 5%; height: "+str(height)+"px ;background-color: #ff7500 ;float: left'></div>"
		html +="<div style='width: 5%; height: "+str(height)+"px ;background-color: #ff7500 ;float: right'></div>"
		html += text
		html += "<footer>You can configure the report at <a href='https://github.com/backup-config'>github</a>. For error_messages only, change the error_report parameter to true. Visit <a href='https://confluence.yours.com/display/NetWorker+Report+FAQ'>confluence</a> for better understanding of the report messages </footer></body></html>"
		message = MIMEText(html,'html')
		message['Subject'] = "Admin Report"
		message['From'] = sender
		message['To'] = self.admin_report_recipient
		server.sendmail(sender,self.admin_report_recipient,message.as_string())
		server.quit()
  
	## @report_send_email will send a Mail with all assoziated backups to a specific contact formated in html
	def report_send_email(self,contacts_relation_to_owner,backup_states,contacts_relation_to_backups):
		backup_states = OrderedDict(sorted(backup_states.items())) # Sorts the list with all backups by their names
		print("Why are no emails send?")
		for recipient in contacts_relation_to_backups.keys() :
			try:
				contacts_relation_to_backups[recipient] = sorted(contacts_relation_to_backups[recipient]) #gets all backups for a specific contact
				sender = self.report_sender + self.maildomain
				data = open(self.config['files']['basedir']+self.config['files']['maillayout'],'r')
				server = smtplib.SMTP(self.mailserver,25,"mail_domain",60)
				if self.debug.lower() == "true":
					server.set_debuglevel(1)
				height = 50
				if recipient == '':
					text = "<p style='text-align: center'>Dear " + " (Owner and mail address are Missing please add them)" +", please find your Backup Report from "+self.now.strftime("%d-%m-%Y %H:%M")+"</p>"
				else:
					text = "<p style='text-align: center'>Dear " + contacts_relation_to_owner[recipient] +", please find your Backup Report from "+self.now.strftime("%d-%m-%Y %H:%M")+"</p>"
				table = "<table border='2' style='width: 90%'>"
				table += "<tr><td>Hostname</td><td>Backup State</td><td>Backup Information</td></tr>"
				found_informations = False
				for backup in  contacts_relation_to_backups[recipient]:
					if backup  in backup_states and 0 < len(backup_states[backup]) :
						hasData = False
						for b in backup_states[backup]:
							if len(b) > 1:
								found_informations = True
								hasData = True
						if hasData == True:
							height += 32 
							table += "<tr><td>" +backup + "</td><td><table>"
							for key in range(0,len(backup_states[backup])) :
                       						if 1 < len(backup_states[backup][key]) and "state" in backup_states[backup][key][1] and backup_states[backup][key][1]['state'] != "" :
                         						table += "<tr><td>" + backup_states[backup][key][1]['state']+"</td></tr>"
							table += "</table></td><td><table>"
							for key in range(0,len(backup_states[backup])) :
								if 'info' in backup_states[backup][key][0] and backup_states[backup][key][0]['info'] != "" :
									table += "<tr><td>"+backup_states[backup][key][0]['info']+"</td></tr>"
							table+= "</table></td></tr>"
				table += "</table></div></div>"
				text += table
				if height < 1100 :
					height = 1100
				html = data.read() + "<div style='width: 5%; height: "+str(height)+"px ;background-color: #ff7500 ;float: left'></div>"
				html +="<div style='width: 5%; height: "+str(height)+"px ;background-color: #ff7500 ;float: right'></div>"
				html += text
				html += "<footer>You can configure the report at <a href='https://github.com/backup-config'>github</a>. For error_messages only, change the error_report parameter to true. Visit <a href='https://confluence.yours.com/display/NetWorker+Report+FAQ'>confluence</a> for better understanding of the report messages </footer></body></html>"
				if recipient == '' :
					recipient = self.error_recipient
				if self.debug == 'true':
					message = MIMEText(html,'html')
					message['Subject'] = "Debug Backup Report"
					message['From'] = sender
					message['To'] = self.error_recipient
					if found_informations == True :
						server.sendmail(sender,self.error_recipient,message.as_string())
						server.quit()
				elif self.debug == 'false':
					message = MIMEText(html,'html')
					message['Subject'] = "Backup Report"
					message['From'] = sender
					message['To'] = recipient
					if found_informations == True :
						server.sendmail(sender,recipient,message.as_string())
						server.quit()
			except:
    				print("Something went wrong while trying to send report email")
    				self.send_error_mail(str(traceback.format_exc())) 

	## @send_group_node_relation_mail sends a mail which displays which vm's are in which group
	def send_group_node_relation_mail(self,group_node_relation):
		sender = self.report_sender + self.maildomain
		data = open(self.config['files']['basedir'] + self.config['files']['maillayout'],'r')
		html = data.read()
		html += "<table border='2' style='width: 90%'>"
		for group in group_node_relation.keys():
			html += "<tr><td>"+group+"</td><td><table>"
			for i in range(0,len(group_node_relation[group])):
				html+="<tr><td>" + group_node_relation[group][i] + "</td></tr>"
			html += "</table></td></tr>"
		html += "</table></div></body></html>"
		serverm = smtplib.SMTP(self.mailserver,25,"mail_domain",60)
		if self.debug.lower() == 'true':
			serverm.set_debuglevel(1)
		else :
			print ("\n Group agent relation will be sended \n")
		message = MIMEText(html,'html')
		message['Subject'] = 'Grould node relation report'
		message['From'] = sender
		message['To'] = self.error_recipient
		serverm.sendmail(sender,self.error_recipient,message.as_string())
		serverm.quit()
