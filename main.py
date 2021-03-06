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

registered_users = ['supernova2468@gmail.com', 'callahanjake1986@gmail.com', 'mattritzj@gmail.com']

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

class BB_Status(ndb.Model):
	state = ndb.BooleanProperty(default=False)
	command = ndb.BooleanProperty(default=False)
	timezone = ndb.IntegerProperty(default=5)
	
def get_status():
	status_key = ndb.Key(BB_Status, 'Beaglebone1')
	status = status_key.get()
	
	if not status:
		status = BB_Status(key=status_key)
		status.put()
	return status
	
class Email_Settings(ndb.Model):
	last_mail = ndb.DateProperty(default=(datetime.date.today()-datetime.timedelta(days=1)))

	temperature_l = ndb.IntegerProperty(default=0)
	current_l = ndb.IntegerProperty(default=0)
	humidity_l = ndb.IntegerProperty(default=0)
	battery_voltage_l = ndb.IntegerProperty(default=0)
	voltage_l = ndb.IntegerProperty(default=0)
	frequency_l = ndb.IntegerProperty(default=0)
	
	temperature_h = ndb.IntegerProperty(default=500)
	current_h = ndb.IntegerProperty(default=500)
	humidity_h = ndb.IntegerProperty(default=500)
	battery_voltage_h = ndb.IntegerProperty(default=500)
	voltage_h = ndb.IntegerProperty(default=500)
	frequency_h = ndb.IntegerProperty(default=500)

def get_email():
	email_key = ndb.Key(Email_Settings, 'Beaglebone1')
	email = email_key.get()
	
	if not email:
		email = Email_Settings(key=email_key)
		email.put()
	return email
	
class Cut_Settings(ndb.Model):
	temperature_l = ndb.IntegerProperty(default=0)
	current_l = ndb.IntegerProperty(default=0)
	humidity_l = ndb.IntegerProperty(default=0)
	battery_voltage_l = ndb.IntegerProperty(default=0)
	voltage_l = ndb.IntegerProperty(default=0)
	frequency_l = ndb.IntegerProperty(default=0)
	
	temperature_h = ndb.IntegerProperty(default=500)
	current_h = ndb.IntegerProperty(default=500)
	humidity_h = ndb.IntegerProperty(default=500)
	battery_voltage_h = ndb.IntegerProperty(default=500)
	voltage_h = ndb.IntegerProperty(default=500)
	frequency_h = ndb.IntegerProperty(default=500)

def get_cut():
	cut_key = ndb.Key(Cut_Settings, 'Beaglebone1')
	cut = cut_key.get()
	
	if not cut:
		cut = Cut_Settings(key=cut_key)
		cut.put()
	return cut
	
class Log(ndb.Model):
	timestamp = ndb.DateTimeProperty('tm', indexed=True)
	temperature = ndb.FloatProperty('t', indexed=False)
	current = ndb.FloatProperty('c', indexed=False)
	humidity = ndb.FloatProperty('h', indexed=False)
	battery_voltage = ndb.FloatProperty('b', indexed=False)
	voltage = ndb.FloatProperty('v', indexed=False)
	frequency = ndb.FloatProperty('f', indexed=False)
	
	unique = ndb.BooleanProperty('u', indexed=True, default=True)
	
	
@app.route('/')
def reroute():
	return redirect(url_for('data'))

@app.route('/data')
def data():
	logs = Log.query(Log.unique == True).order(Log.timestamp)
	
	data_table = [['Time','(*F)','(%)','(V)','(A)','(V)','(Hz)','(W)']]
	
	for log in logs:
		data_table.append([log.timestamp.ctime(), 
								log.temperature, 
								log.humidity, 
								log.voltage, 
								log.current, 
								log.battery_voltage, 
								log.frequency,
								round(log.voltage * log.current,1)])

		
	return render_template('index.html', data_table = data_table)

@app.route('/post')
def post():

	# create entities
	new_log = Log()
	status = get_status()
	
	# fill data
	string_time = request.args.get('timestamp')
	new_log.timestamp = datetime.datetime.fromtimestamp(float(string_time)) - datetime.timedelta(hours=status.timezone)
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
		check = log_check(new_log)
		if check['check']:
			send_mail(check['value'], check['variable'])

	cutoff = get_cut()
	
	reply_string = '{},{},{},{},{},{},{},{},{},{},{},{},{}'
	return reply_string.format(status.command,
							cutoff.battery_voltage_l,cutoff.battery_voltage_h,
							cutoff.current_l,cutoff.current_h,
							cutoff.frequency_l,cutoff.frequency_h,
							cutoff.humidity_l,cutoff.humidity_h,
							cutoff.temperature_l,cutoff.temperature_h,
							cutoff.voltage_l,cutoff.voltage_h)

def log_check(log):
	es = get_email()
	
	v = log.voltage
	if v > es.voltage_h or v < es.voltage_l:
		return {'check': True, 'value': v, 'variable': 'voltage'}
	v = log.temperature
	if v > es.temperature_h or v < es.temperature_l:
		return {'check': True, 'value': v, 'variable': 'temperature'}
	v = log.humidity
	if v > es.humidity_h or v < es.humidity_l:
		return {'check': True, 'value': v, 'variable': 'humidity'}
	v = log.current
	if v > es.current_h or v < es.current_l:
		return {'check': True, 'value': v, 'variable': 'current'}
	v = log.battery_voltage
	if v > es.battery_voltage_h or v < es.battery_voltage_l:
		return {'check': True, 'value': v, 'variable': 'battery_voltage'}
	v = log.frequency
	if v > es.frequency_h or v < es.frequency_l:
		return {'check': True, 'value': v, 'variable': 'frequency'}		
				
	return {'check': False, 'value': 0, 'variable': '0'}
	
def send_mail(value, variable):
	#check if one has already been sent today
	email_settings = get_email()
	if email_settings.last_mail == datetime.date.today():
		return
		
	sender_address = 'Smart Relay <smart-relay@appspot.gserviceaccount.com>'
	subject = 'Variable {} has gone out of range at {}'.format(variable,value)
    
	for user in registered_users:
		mail.send_mail(sender_address, user, subject, ' ')
	email_settings.last_mail = datetime.date.today()
	email_settings.put()
	
@app.route('/control')
def control():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/control'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/control'))
	
	status = get_status()
	
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
		if abs(last_update - datetime.datetime.now() + datetime.timedelta(hours=status.timezone)) > datetime.timedelta(minutes=1.1):
			output = '<span class="label label-default">Device Offline</span>'
	except IndexError:
		last_update = 0
		output = '<span class="label label-default">Device Offline</span>'
        

	
	if status.command:
		button = 'class="label label-success">Startup Requested'
	else:
		button = 'class="label label-danger">Shutdown Requested'
	
	return render_template('control.html', state = output, uptime = uptime, button = button, last_update = last_update)

@app.route('/control2')
def control2():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/control'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/control'))

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
	query = Log.query(Log.unique == True).order(Log.timestamp)
	
	out_log = "Timestamp,Temperature (F),Humidity (%),Current (A),Voltage (V),Battery Voltage (V),Frequency (Hz)<br>"
	format_string = '{},{},{},{},{},{},{}<br>'
	for log in query:
		out_log += format_string.format(log.timestamp, log.temperature, log.humidity, log.current, log.voltage, log.battery_voltage, log.frequency)

	return str(out_log)

@app.route('/setup')
def thresh_setup():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/setup'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/setup'))
	email_settings = get_email()
	
	return render_template('setup.html', 
				voltage_l = email_settings.voltage_l, voltage_h = email_settings.voltage_h,
				humidity_l = email_settings.humidity_l, humidity_h = email_settings.humidity_h,
				temperature_l = email_settings.temperature_l, temperature_h = email_settings.temperature_h,
				current_l = email_settings.current_l, current_h = email_settings.current_h,
				battery_voltage_l = email_settings.battery_voltage_l, battery_voltage_h = email_settings.battery_voltage_h,
				frequency_l = email_settings.frequency_l, frequency_h = email_settings.frequency_h)

@app.route('/setup2', methods=['POST'])
def thresh_post():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/setup'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/setup'))

	email_settings = get_email()
	
	try:
		email_settings.voltage_l = int(request.form['voltage_l'])
	except ValueError:
		pass
	try:
		email_settings.voltage_h = int(request.form['voltage_h'])
	except ValueError:
		pass
		
	try:
		email_settings.temperature_l = int(request.form['temperature_l'])
	except ValueError:
		pass
	try:
		email_settings.temperature_h = int(request.form['temperature_h'])
	except ValueError:
		pass

	try:
		email_settings.humidity_l = int(request.form['humidity_l'])
	except ValueError:
		pass
	try:
		email_settings.humidity_h = int(request.form['humidity_h'])
	except ValueError:
		pass

	try:
		email_settings.current_l = int(request.form['current_l'])
	except ValueError:
		pass
	try:
		email_settings.current_h = int(request.form['current_h'])
	except ValueError:
		pass

	try:
		email_settings.battery_voltage_l = int(request.form['battery_voltage_l'])
	except ValueError:
		pass
	try:
		email_settings.battery_voltage_h = int(request.form['battery_voltage_h'])
	except ValueError:
		pass

	try:
		email_settings.frequency_l = int(request.form['frequency_l'])
	except ValueError:
		pass
	try:
		email_settings.frequency_h = int(request.form['frequency_h'])
	except ValueError:
		pass		
	
	email_settings.put()
	
	return redirect(url_for('thresh_setup'))
	
@app.route('/cutoff')
def cut_setup():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/cutoff'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/cutoff'))
	cut_settings = get_cut()
	
	return render_template('cutoffsetup.html', 
				voltage_l = cut_settings.voltage_l, voltage_h = cut_settings.voltage_h,
				humidity_l = cut_settings.humidity_l, humidity_h = cut_settings.humidity_h,
				temperature_l = cut_settings.temperature_l, temperature_h = cut_settings.temperature_h,
				current_l = cut_settings.current_l, current_h = cut_settings.current_h,
				battery_voltage_l = cut_settings.battery_voltage_l, battery_voltage_h = cut_settings.battery_voltage_h,
				frequency_l = cut_settings.frequency_l, frequency_h = cut_settings.frequency_h)

@app.route('/cutoffsetup2', methods=['POST'])
def cut_post():
	code = check_auth()	
	if code == 1:
		return redirect(users.create_login_url('/cutoff'))
	if code == 2:
		return render_template('badlogin.html', url = users.create_logout_url('/cutoff'))

	cut_settings = get_cut()
	
	try:
		cut_settings.voltage_l = int(request.form['voltage_l'])
	except ValueError:
		pass
	try:
		cut_settings.voltage_h = int(request.form['voltage_h'])
	except ValueError:
		pass
		
	try:
		cut_settings.temperature_l = int(request.form['temperature_l'])
	except ValueError:
		pass
	try:
		cut_settings.temperature_h = int(request.form['temperature_h'])
	except ValueError:
		pass

	try:
		cut_settings.humidity_l = int(request.form['humidity_l'])
	except ValueError:
		pass
	try:
		cut_settings.humidity_h = int(request.form['humidity_h'])
	except ValueError:
		pass

	try:
		cut_settings.current_l = int(request.form['current_l'])
	except ValueError:
		pass
	try:
		cut_settings.current_h = int(request.form['current_h'])
	except ValueError:
		pass

	try:
		cut_settings.battery_voltage_l = int(request.form['battery_voltage_l'])
	except ValueError:
		pass
	try:
		cut_settings.battery_voltage_h = int(request.form['battery_voltage_h'])
	except ValueError:
		pass

	try:
		cut_settings.frequency_l = int(request.form['frequency_l'])
	except ValueError:
		pass
	try:
		cut_settings.frequency_h = int(request.form['frequency_h'])
	except ValueError:
		pass		
	
	cut_settings.put()
	
	return redirect(url_for('cut_setup'))
	
def check_auth():
	user = users.get_current_user()
	
	if not user:
		return 1		
	
	if user.email() not in registered_users:
		return 2
		
	return 0

@app.route('/cron')
def cron():
	query = Log.query().order(Log.timestamp)
	
	previous_rank = 0
	for log in query:
		current_rank = log.temperature + log.humidity + log.voltage + log.current + log.battery_voltage + log.frequency
		if abs(current_rank - previous_rank) > 2:
			log.unique = True
			log.put()
			previous_rank = current_rank
		else:
			log.unique = False
			log.put()

	return '',200

	

@app.errorhandler(404)
def page_not_found(e):
    return 'Sorry, nothing at this URL.', 404
