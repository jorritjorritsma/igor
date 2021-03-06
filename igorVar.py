#!/usr/bin/env python
import argparse
import urlparse
import urllib
import httplib2
import sys
import os
import time
import json
import pprint
import xml.etree.ElementTree

DEFAULT_URL="http://framboos.local:9333/data"
if 'IGORSERVER_URL' in os.environ:
	DEFAULT_URL = os.environ['IGORSERVER_URL']
VERBOSE=False

class IgorServer:
	def __init__(self, url, bearer_token=None, access_token=None):
		self.baseUrl = url
		if url[-1] != '/':
			url = url + '/'
		self.url = url
		self.bearer_token = bearer_token
		self.access_token = access_token
		
	def get(self, item, variant=None, format=None):
		if format == None:
			format = 'application/xml'
		return self._action("GET", item, variant, format)
		
	def delete(self, item, variant=None, format=None):
		if variant == None:
			variant = "ref"
		if format == None:
			format = "text/plain"
		return self._action("DELETE", item, variant, format)
		
	def put(self, item, data, datatype, variant=None, format=None):
		if format == None:
			format = 'text/plain'
		return self._action("PUT", item, variant, format, data=data, datatype=datatype)
		
	def post(self, item, data, datatype, variant=None, format=None):
		if format == None:
			format = 'text/plain'
		return self._action("POST", item, variant, format, data=data, datatype=datatype)
		
	def _action(self, method, item, variant, format=None, data=None, datatype=None):
		url = urlparse.urljoin(self.url, item)
		query = {}
		if variant:
			query['.VARIANT'] = variant
		if self.access_token:
			query['access_token'] = self.access_token
		if query:
			assert not '?' in url
			url = url + '?' + urllib.urlencode(query)
		headers = {}
		if format:
			headers['Accept'] = format
		if datatype:
			headers['Content-Type'] = datatype
		if self.bearer_token:
			headers['Authorization'] = 'Bearer %s' % self.bearer_token
		h = httplib2.Http()
		if VERBOSE:
			print >>sys.stderr, ">>> GET", url
			print >>sys.stderr, "... Headers", headers
			if data:
				print >>sys.stderr, "... Data", repr(data)
		reply, content = h.request(url, method=method, headers=headers, body=data)
		if VERBOSE:
			print >>sys.stderr, "<<< Headers", reply
			print >>sys.stderr, "...", repr(content)
		if not 'status' in reply or reply['status'] != '200':
			msg = "%s: Error %s for %s" % (sys.argv[0], reply['status'], url)
			contentLines = content.splitlines()
			if len(contentLines) == 1:
				print >>sys.stderr, msg + ':' + contentLines[0]
			else:
				print >>sys.stderr, msg
				print >>sys.stderr, content
			sys.exit(1)
		return content
		
def main():
	global VERBOSE
	parser = argparse.ArgumentParser(description="Access Igor home automation service and other http databases")
	parser.add_argument("-u", "--url", help="Base URL of the server (default: %s, environment IGORSERVER_URL)" % DEFAULT_URL, default=DEFAULT_URL)
	parser.add_argument("-e", "--eval", action="store_true", help="Evaluate XPath expression in stead of retrieving variable (by changing /data to /evaluate in URL)")
	parser.add_argument("-v", "--variant", help="Variant of data to get (or put, post)")
	parser.add_argument("-M", "--mimetype", help="Get result as given mimetype")
	parser.add_argument("--text", dest="mimetype", action="store_const", const="text/plain", help="Get result as plain text")
	parser.add_argument("--json", dest="mimetype", action="store_const", const="application/json", help="Get result as JSON")
	parser.add_argument("--xml", dest="mimetype", action="store_const", const="application/xml", help="Get result as XML")
	parser.add_argument("--python", action="store_true", help="Get result as Python (converted from JSON)")
	parser.add_argument("--pretty", action="store_true", help="Pretty-print result (only for Python, currently)")
	parser.add_argument("--verbose", action="store_true", help="Print what is happening")
	parser.add_argument("--delete", action="store_true", help="Delete variable")
	parser.add_argument("--create", action="store_true", help="Create or clear a variable")
	parser.add_argument("--put", metavar="MIMETYPE", help="PUT data of type MIMETYPE, from --data or stdin")
	parser.add_argument("--post", metavar="MIMETYPE", help="POST data of type MIMETYPE, from --data or stdin")
	parser.add_argument("--data", metavar="DATA", help="POST or PUT DATA, in stead of reading from stdin")
	parser.add_argument("--checkdata", action="store_true", help="Check that data is valid XML or JSON")
	parser.add_argument("--timestamp", action="store_true", help="Add lastActivity timestamp to XML or JSON data")
	parser.add_argument("-0", "--allow-empty", action="store_true", help="Allow empty data from stdin")
	parser.add_argument("--bearer", metavar="TOKEN", help="Add Authorization: Bearer TOKEN header line")
	parser.add_argument("--access", metavar="TOKEN", help="Add access_token=TOKEN query argument")
	
	parser.add_argument("var", help="Variable to retrieve")
	args = parser.parse_args()
	VERBOSE=args.verbose
	
	url = args.url
	if args.eval:
		url.replace("/data", "/evaluate")
	server = IgorServer(url, bearer_token=args.bearer, access_token=args.access)
	if args.python:
		args.mimetype = 'application/json'
	if args.delete:
		result = server.delete(args.var)
	elif args.create:
		result = server.put(args.var, '{}', 'application/json', variant=args.variant, format=args.mimetype)
	elif args.put:
		data = args.data
		if data is None:
			data = sys.stdin.read()
		if args.checkdata or args.timestamp:
			# Check that data is valid JSON or XML.
			# If no data is read at all only exit with nonzero status, assume the previous
			# part of the pipeline has already issues an error.
			if not data:
				sys.exit(1)
			if args.put == 'application/json':
				try:
					decodedData = json.loads(data)
					if args.timestamp:
						decodedData['lastActivity'] = str(int(time.time()))
					data = json.dumps(decodedData)
				except ValueError:
					print >>sys.stderr, "%s: no valid JSON data read from stdin" % sys.argv[0]
					sys.exit(1)
			elif args.put == 'application/xml':
				try:
					decodedData = xml.etree.ElementTree.fromstring(data)
					if args.timestamp:
						n = xml.etree.ElementTree.SubElement(decodedData, 'lastActivity')
						n.text = str(int(time.time()))
						data = xml.etree.ElementTree.tostring(decodedData)
				except xml.etree.ElementTree.ParseError:
					print >> sys.stderr, "%s: no valid XML data read from stdin" % sys.argv[0]
					sys.exit(1)
			else:
				print >>sys.stderr, "%s: --checkdata and --timestamp only allowed for JSON and XML data"
				sys.exit(1)
		elif not data and not args.allow_empty:
			print >>sys.stderr, '%s: no data read from stdin' % sys.argv[0]
			sys.exit(1)
		result = server.put(args.var, data, args.put, variant=args.variant, format=args.mimetype)
	elif args.post:
		data = args.data
		if not data:
			data = sys.stdin.read()
		result = server.post(args.var, data, args.post, variant=args.variant, format=args.mimetype)
	else:
		result = server.get(args.var, variant=args.variant, format=args.mimetype)
	if args.python:
		result = json.loads(result)
		if args.pretty:
			pp = pprint.PrettyPrinter()
			result = pp.pformat(result)
		else:
			result = repr(result)
	print result.strip()
	
if __name__ == '__main__':
	main()
	
	
