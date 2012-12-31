import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import re
import os
import time
import cgi
import sys
import json

# Global settings
__plugin__		= "ShareThe.TV"
__version__		= "2.0.0"
__addonID__		= "script.sharethetv"
__settings__ = xbmcaddon.Addon(__addonID__)
__apiurl__ = 'http://sharethe.tv/api/'

# Debugging info
print "[ADDON] '%s: version %s' initialized!" % (__plugin__, __version__)


# Send a notice.  Specify message and duration.
def sendNotice(msg, time):
	xbmc.executebuiltin('Notification(' + __plugin__ + ',' + msg + ',' + time +',' + __settings__.getAddonInfo("icon") + ')')


def debug(message):
	message = "ShareThe.TV: " + message
	if (__settings__.getSetting( "debug" ) == 'true'):
		print message.encode('ascii', 'ignore')


# Query the movie list
def getMovieLibrary():
	rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params':{'properties': ['year', 'imdbnumber']}, 'id': 1})

	result = xbmc.executeJSONRPC(rpccmd)
	result = json.loads(result)

	try:
		error = result['error']
		debug("getMovieLibrary: " + str(error))
		return None
	except KeyError:
		pass

	try:
		return result['result']['movies']
	except KeyError:
		debug("getMovieLibrary: KeyError: result['result']['movies']")
		return None


# Build out movie XML based on getMovieLibrary() call.  Watch for special chars in title
def buildMovieXML(movies):
	debug("buildMovieXML")
	movielist = "<movies>"
	for i in range(0, len(movies)):
		movielist += "<movie>"
		movielist += "<imdb>" + movies[i]['imdbnumber'] + "</imdb>"
		movielist += "<title>" + cgi.escape(movies[i]['label']) + "</title>"
		movielist += "<year>" + str(movies[i]['year']) + "</year>"
		movielist += "</movie>"
	movielist += "</movies>"
	return movielist.encode('ascii', 'ignore')


# Build out parameters list including user/pass, and movie list
def buildParamsXML(movielist):
	debug("buildParamsXML")
	params = "<user>"
	params += "<version>" + __version__ + "</version>"
	params += "<email>" + __settings__.getSetting("email") + "</email>"
	params += "<password>" + __settings__.getSetting("password") + "</password>"
	params += movielist
	params += "</user>"
	return params


# Send the request and handle returned errors
def sendRequest(params):
	req = urllib2.Request(url=__apiurl__, data=params, headers={'Content-Type': 'application/xml'})
	try:
		response = urllib2.urlopen(req)
		sendNotice("Library update sent", "5000")
	except urllib2.URLError, e:
		try:
			if e.code == 202:
				if (__settings__.getSetting( "notifications" ) == 'true'):
					sendNotice("Library update sent.", "5000")
			elif e.code == 204:
				sendNotice("Empty movie library so not sending update.", "7000")
			elif e.code == 401:
				sendNotice("Authentication failed.", "5000")
			elif e.code == 403:
				sendNotice("Please update your addon before submitting.", "7000")
			else:
				sendNotice("Unexpected error.", "5000")
		except AttributeError:
			sendNotice("Unable to contact server, but try again soon.", "5000")


def sendUpdate():
	if (__settings__.getSetting("email") == '' or __settings__.getSetting("password") == ''):
		sendNotice("Configure your account details before submitting.", "6000")
		return
	
	movielist = buildMovieXML(getMovieLibrary())
	debug('Movielist is: ' + movielist)
	
	params = buildParamsXML(movielist)
	
	sendRequest(params)


# Main execution path
sendUpdate()

