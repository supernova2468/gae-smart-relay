import os
import json
import datetime
import csv

from flask import Flask
from flask import request, redirect, url_for, render_template
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import mail


app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

class BB_Status(ndb.Model):
	state = ndb.BooleanProperty(default=False)
	command = ndb.BooleanProperty(default=False)
	last_mail = ndb.DateTimeProperty()
    
    
	#temperature = ndb.FloatProperty(repeated=True, default=[0,500])
	#current = ndb.FloatProperty(repeated=True, default=[0,500])
	#humidity = ndb.FloatProperty(repeated=True, default=[0,500])
	#battery_voltage = ndb.FloatProperty(repeated=True, default=[0,500])
	#voltage = ndb.FloatProperty(repeated=True, default=[0,500])
	#frequency = ndb.FloatProperty(repeated=True, default=[0,500])

def get_status():
	status_key = ndb.Key(BB_Status, 'Beaglebone1')
	status = status_key.get()
	
	if not status:
		status = BB_Status(key=status_key)
		status.put()
	return status

class Log(ndb.Model):
	timestamp = ndb.DateTimeProperty('tm', indexed=True)
	temperature = ndb.FloatProperty('t', indexed=False)
	current = ndb.FloatProperty('c', indexed=False)
	humidity = ndb.FloatProperty('h', indexed=False)
	battery_voltage = ndb.FloatProperty('b', indexed=False)
	voltage = ndb.FloatProperty('v', indexed=False)
	frequency = ndb.FloatProperty('f', indexed=False)
	
	
@app.route('/')
def reroute():
	return redirect(url_for('data'))

@app.route('/data')
def data():
	logs = Log.query().order(Log.timestamp)
	
	data_table = [['Time','Temperature','Humidity','Voltage','Current','Battery Voltage','Frequency']]
	
	for log in logs:
		data_table.append([log.timestamp.ctime(), log.temperature, log.humidity, log.voltage, log.current, log.battery_voltage, log.frequency])

		
	return render_template('index.html', data_table = data_table)

@app.route('/post')
def post():

	# create entities
	new_log = Log()
	status_key = ndb.Key(BB_Status, 'Beaglebone1')
	status = status_key.get()
	
	if not status:
		status = BB_Status(key=status_key)
		status.put()
	
	# fill data
	string_time = request.args.get('timestamp')
	new_log.timestamp = datetime.datetime.fromtimestamp(float(string_time))
	new_log.temperature = float(request.args.get('temperature'))
	new_log.current = float(request.args.get('current'))
	new_log.humidity = float(request.args.get('humidity'))
	new_log.battery_voltage = float(request.args.get('battery_voltage'))
	new_log.voltage = float(request.args.get('voltage'))
	new_log.frequency = float(request.args.get('frequency'))
	password = request.args.get('password')
	
	if request.args.get('state') == 'True':
		status.state = True
	else:
		status.state = False
		
	# save data
	if password == 'my_password':
		new_log.put()
		status.put()
        send_mail('test', 50)
	return str(status.command)

def send_mail(value, variable):
    #check if one has already been sent today
    
    sender_address = 'Smart Relay <smart-relay@appspot.gserviceaccount.com>'
    subject = 'Value {} has gone out of range at {}'.format(value,variable)
    
    mail.send_mail(sender_address, 'supernova2468@gmail.com', subject, ' ')
	
@app.route('/control')
def control():
	user = users.get_current_user()
	
	if not user:
		return redirect(users.create_login_url())

	
	status_key = ndb.Key(BB_Status, 'Beaglebone1')
	status = status_key.get()
	if not status:
		status = BB_Status(key=status_key)
		status.put()
	
	if status.state:
		output = '<span class="label label-success">Outlet Powered On</span>' 
	else:
		output = '<span class="label label-danger">Outlet Powered Off</span>'
		
		
	#calculate last 24h on 1 min posting
	time = datetime.datetime.now() - datetime.timedelta(days=1)
	
	query = Log.query(Log.timestamp > time).order(-Log.timestamp)
	
	
	uptime = query.count()
	uptime = (uptime * 100) / 1440
	try:
		last_update = query.fetch(1)[0].timestamp
	except IndexError:
		last_update = 0
	
	if status.command:
		button = 'class="label label-success">Startup Requested'
	else:
		button = 'class="label label-danger">Shutdown Requested'
	
	return render_template('control.html', state = output, uptime = uptime, button = button, last_update = last_update)

@app.route('/control2')
def control2():
	user = users.get_current_user()
	
	if not user:
		return redirect(users.create_login_url())

	status_key = ndb.Key(BB_Status, 'Beaglebone1')
	status = status_key.get()
	
	if status.command:
		status.command = False
	else:
		status.command = True
		
	status.put()
	return redirect(url_for('control'))
	
@app.route('/csv')
def csv():
	query = Log.query()
	query.order(Log.timestamp)
	
	out_log = "Timestamp,Temperature,Humidity,Current,Voltage,Battery Voltage,Frequency<br>"
	format_string = '{},{},{},{},{},{},{}<br>'
	for log in query:
		out_log += format_string.format(log.timestamp, log.temperature, log.humidity, log.current, log.voltage, log.battery_voltage, log.frequency)

	return str(out_log)

@app.route('/setup')
def thresh_setup():
    return 'not done yet'

@app.errorhandler(404)
def page_not_found(e):
    return 'Sorry, nothing at this URL.', 404
