import time
import ConfigParser
import subprocess
import requests
import urlparse
import RPi.GPIO as GPIO

parser = ConfigParser.ConfigParser()
parser.read(['todowatch.conf'])

api_base = parser.get('global', 'api_base')
pin_connected = int(parser.get('global', 'pin_connected'))
pin_complete = int(parser.get('global', 'pin_complete'))
sound = None
if parser.has_option('global', 'sound'):
	sound = parser.get('global', 'sound')

GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_connected, GPIO.OUT)
GPIO.setup(pin_complete, GPIO.OUT)

def get(uri, headers=None):
	uri = make_absolute(uri)
	if '?' in uri:
		uri += '&from=rpi'
	else:
		uri += '?from=rpi'
	while True:
		try:
			print 'GET %s' % uri
			resp = requests.get(uri, headers=headers, timeout=30)
			if resp.status_code != 200:
				print 'bad response: %d' % resp.status_code
				time.sleep(1)
				continue
			break
		except KeyboardInterrupt:
			raise
		except:
			print 'failed, retrying'
			time.sleep(1)
	print resp.text
	return resp

def make_absolute(uri):
	if '://' in uri:
		return uri
	base_parsed = urlparse.urlparse(api_base)
	rel_parsed = urlparse.urlparse(uri)
	uri = '%s://%s%s' % (base_parsed.scheme, base_parsed.netloc, rel_parsed.path)
	if rel_parsed.query:
		uri += '?' + rel_parsed.query
	return uri

def set_completed(on):
	if on:
		GPIO.output(pin_complete, GPIO.HIGH)
		if sound:
			subprocess.check_call(['aplay', sound])
	else:
		GPIO.output(pin_complete, GPIO.LOW)

def get_changes_uri(resp):
	link = resp.headers.get('link')
	if link and 'changes-wait' in link:
		end = link.find('>')
		if end != -1:
			return link[1:end]
	return None

GPIO.output(pin_connected, GPIO.LOW)

# get initial
uri = api_base + '/'
resp = get(uri)
items = resp.json()

completed = True
for i in items:
	if not i.get('completed'):
		completed = False
		break

set_completed(completed)

while True:
	uri = get_changes_uri(resp)
	assert(uri)
	print 'changes-wait: %s' % uri
	GPIO.output(pin_connected, GPIO.HIGH)

	resp = get(uri, headers={'Wait': 25})
	items = resp.json()
	if len(items) >= 1:
		total_items = int(items[0]['total-items'])
		total_completed = int(items[0]['total-completed'])
		was_completed = completed
		completed = (total_items == total_completed)
		if completed != was_completed:
			set_completed(completed)
