import os
import time
import ConfigParser
import traceback
import subprocess

class WifiConfig(object):
	def __init__(self):
		self.ssid = ''
		self.password = None

	def compare(self, other):
		if self.ssid != other.ssid:
			return False
		if self.password != other.password:
			return False
		return True

def read_config(path):
	parser = ConfigParser.ConfigParser()
	parser.read([path])
	if not parser.has_option('global', 'ssid'):
		return
	config = WifiConfig()
	config.ssid = parser.get('global', 'ssid')
	if parser.has_option('global', 'password'):
		config.password = parser.get('global', 'password')
	return config

def poll_for_config():
	out = subprocess.check_output(['findmnt', '--list', '--output', 'TARGET'])
	for line in out.split('\n'):
		if line.endswith('\n'):
			line = line[:-1]
		if not line or line == 'TARGET':
			continue
		path = line
		if not path.startswith('/media/'):
			continue
		fpath = os.path.join(path, 'wifi.conf')
		if not os.path.exists(fpath):
			continue
		config = read_config(fpath)
		return (fpath, config)
	return (None, None)

def apply_config(config):
	out =  'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
	out += 'update_config=1\n'
	out += 'country=US\n'
	out += '\n'
	if config.ssid:
		out += 'network={\n'
		out += '\tssid="%s"\n' % config.ssid
		if config.password:
			out += '\tpsk="%s"\n' % config.password
			out += '\tkey_mgmt="WPA-PSK"\n'
		out += '}\n'

	f = open('/tmp/wpa_supplicant.conf', 'w')
	f.write(out)
	f.close()
	os.rename('/tmp/wpa_supplicant.conf', '/etc/wpa_supplicant/wpa_supplicant.conf')

cur_config = WifiConfig()

while True:
	try:
		path, config = poll_for_config()
		if config is not None and not config.compare(cur_config):
			cur_config = config
			apply_config(config)
			print 'updated config from %s' % path
	except:
		traceback.print_exc()
	time.sleep(1)
