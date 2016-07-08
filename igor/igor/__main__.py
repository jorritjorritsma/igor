import webApp
import xmlDatabase
import actions
import sseListener
import callUrl
import os
import argparse
import besthostname
import time
import json
import web

import sys
reload(sys)
sys.setdefaultencoding('utf8')

DATADIR=os.path.dirname(__file__)

class IgorServer:
    def __init__(self, datadir, port=9333):
        #
        # Create the database, and tell the web application about it
        #
        self.port = port
        self.app = webApp.WEBAPP
        self.database = xmlDatabase.DBImpl(os.path.join(datadir, 'database.xml'))
        webApp.DATABASE = self.database # Have to set in a module-global variable, to be fixed some time...
        webApp.SCRIPTDIR = os.path.join(datadir, 'scripts')
        webApp.PLUGINDIR = os.path.join(datadir, 'plugins')
        webApp.STATICDIR = os.path.join(datadir, 'static')
        webApp.COMMANDS = self
        
        #
        # Create and start the asynchronous URL accessor
        #
        self.urlCaller = callUrl.URLCaller(self.app)
        self.urlCaller.start()
        
        #
        # Fill self data
        #        
        self.fillSelfData()
        #
        # Startup other components
        #
        self.actionHandler = None
        self.updateActions()
        self.eventSources = None
        self.updateEventSources()
        #
        # Send start action to start any plugins
        #
        self.urlCaller.callURL(dict(method='GET', url='/action/start'))
    
    
    def fillSelfData(self):
        """Put our details in the database"""
        hostName = besthostname.besthostname()
        url = 'http://%s:%d/data' % (hostName, self.port)
        data = dict(host=hostName, url=url, port=self.port, startTime=int(time.time()))
        tocall = dict(method='PUT', url='/data/devices/igor', mimetype='application/json', data=json.dumps(data))
        self.urlCaller.callURL(tocall)
        
    def run(self):
        self.app.run(port=self.port)
        
    def dump(self):
        rv = ''
        if self.urlCaller: rv += self.urlCaller.dump()
        if self.actionHandler: rv += self.actionHandler.dump()
        if self.eventSources: rv += self.eventSources.dump()
        return rv
    def updateActions(self):
        """Create any (periodic) event handlers defined in the database"""
        startupActions = self.database.getElements('actions')
        if len(startupActions):
            if len(startupActions) > 1:
                raise web.HTTPError('401 only one <actions> element allowed')
            if not self.actionHandler:
                self.actionHandler = actions.ActionCollection(self.database, self.urlCaller.callURL)
            self.actionHandler.updateActions(startupActions[0])
        elif self.actionHandler:
            self.actionHandler.updateActions([])

    def updateEventSources(self):
        """Create any SSE event sources that are defined in the database"""
        eventSources = self.database.getElements('eventSources')
        if len(eventSources):
            if len(eventSources) > 1:
                raise web.HTTPError('401 only one <eventSources> element allowed')
            if not self.eventSources:
                self.eventSources = sseListener.EventSourceCollection(self.database, self.urlCaller.callURL)
            self.eventSources.updateEventSources(eventSources[0])
        elif self.eventSources:
            self.eventSources.updateEventSources([])

    def runAction(self, actionname):
        if not self.actionHandler:
            raise web.notfound()
        nodes = self.database.getElements('actions/action[name="%s"]'%actionname)
        if not nodes:
            raise web.notfound()
        for node in nodes:
            self.actionHandler.triggerAction(node)
            
    def save(self):
        self.database.saveFile()
        
    def started(self):
        return "IgorServer started"
    
def main():
    DEFAULTDIR="igorDatabase"
    if 'IGORSERVER_DIR' in os.environ:
        DEFAULTDIR = os.environ['IGORSERVER_DIR']
    DEFAULTPORT=9333
    if 'IGORSERVER_PORT' in os.environ:
        DEFAULTDIR = int(os.environ['IGORSERVER_PORT'])
        
    parser = argparse.ArgumentParser(description="Run the Igor home automation server")
    parser.add_argument("-d", "--database", metavar="DIR", help="Database and scripts are stored in DIR (default: %s, environment IGORSERVER_DIR)" % DEFAULTDIR, default=DEFAULTDIR)
    parser.add_argument("-p", "--port", metavar="PORT", type=int, help="Port to serve on (default: 9333, environment IGORSERVER_PORT)", default=DEFAULTPORT)
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    if args.debug:
        callUrl.DEBUG = True
        sseListener.DEBUG = True
        actions.DEBUG = True
        xmlDatabase.DEBUG = True
        webApp.DEBUG = True
    datadir = args.database
    igorServer = IgorServer(datadir, args.port)
    igorServer.run()
    
main()

    