#!/usr/bin/python
import blescan
import web
import copy
import json
import threading
import sys
import time

AVAILABLE_TIMEOUT=120   # A device is marked unavailable if it hasn't been seen for 2 minutes

KEYS=['available', 'lastSeen', 'firstSeen', 'rssi']

urls=(
    '/ble', 'getBLEdata',
    )

app = web.application(urls, globals())

class BleScanServer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.initScanner()
        self.devices = {}
        self.lock = threading.RLock()
        self.significantChange = False
        print 'inited', repr(self)
        
    def initScanner(self):
        self.scanner = blescan.BleScanner()
        self.scanner.open(0)
        self.startScanning()
    
    def startScanning(self):
        self.scanner.hci_le_set_scan_parameters()
        self.scanner.hci_enable_le_scan()
        self.scanner.enable_filter()

    def stopScanning(self):
        self.scanner.disable_filter()
        self.scanner.hci_disable_le_scan()
        
    def uninitScanner(self):
    	self.stopScanning()
        self.scanner = None

    def run(self):
    	#print 'run in', repr(self)
        try:
            while True:
                evt = self.scanner.parse_advertisement()
                if not evt:
                	#print 'Restarting scan'
                	self.stopScanning()
                	self.startScanning()
                else:
					#print 'event', evt
					self.processEvent(**evt)
        finally:
            #print 'run loop exiting'
            self.uninitScanner()
            #sys.exit(1)
            
    def processEvent(self, address=None, **args):
        if not address:
        	print 'event without address'
        	return
        with self.lock:
            args['lastSeen'] = time.time()
            args['available'] = True
            if not address in self.devices:
                # New device, store the data
                self.devices[address] = args
                self.significantChange = True
            else:
                # Old device, update the data
                for k, v in args.items():
                    self.devices[address][k] = v
            if not 'firstSeen' in self.devices[address]:
                # Update timestamp for first time we saw the device (in a sequence)
                self.devices[address]['firstSeen'] = time.time()
        #print 'devices is now', self.devices
            
    def updateDevices(self):
        with self.lock:
            now = time.time()
            toDelete = []
            for address, data in self.devices.items():
                available = data['lastSeen'] > now - AVAILABLE_TIMEOUT
                if available != data['available']:
                    self.significantChange = True
                data['available'] = available
                if not available:
                    if 'firstSeen' in data:
                        del data['firstSeen']
                    # Delete devices not seen for 24 hours
                    if time.time() - data['lastSeen'] > 24*60*60:
                    	toDelete.append(address)
            for address in toDelete:
            	del self.devices[address]
            #print 'devices is now', self.devices
                        
    def getDevices(self):
        with self.lock:
            #print 'devices=', repr(self), self.devices
            self.updateDevices()
            self.significantChange = False
            return copy.deepcopy(self.devices)

# Module may get imported twice (see http://webpy.org/cookbook/session_with_reloader)
# so use a trick to make sure we have only one ble scanner
if web.config.get('_bleScanner') is None:
	bleScanner = BleScanServer()
	bleScanner.start()
	web.config._bleScanner = bleScanner
else:
	bleScanner = web.config.get('_bleScanner')
            
class getBLEdata:
    def GET(self, name=None):
        devices = bleScanner.getDevices()
        devList = []
        for address, values in devices.items():
        	item = {'address':address}
        	for k in KEYS:
        		if k in values:
        			item[k] = values[k]
        	devList.append(item)
        web.header('Content-Type', 'application/json')
        rv = json.dumps({'bleDevice':devList, 'lastActivity' : time.time()})
        return rv
        
if __name__ == '__main__':
    app.run()
    print 'stopping...'
