import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import re
import os
import time
from urllib2 import URLError, HTTPError

# Global settings
__plugin__		= "ShareThe.TV"
__version__		= "1.0.1"
__addonID__		= "script.sharethetv"
__settings__ = xbmcaddon.Addon(__addonID__)
__apiurl__ = 'http://localhost:3000/api/'

# Auto exec info
AUTOEXEC_PATH = xbmc.translatePath( 'special://home/userdata/autoexec.py' )
AUTOEXEC_FOLDER_PATH = xbmc.translatePath( 'special://home/userdata/' )
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/script.sharethetv/default.py,-startup)")\n'

# Debugging info
print "[ADDON] '%s: version %s' initialized!" % (__plugin__, __version__)


# Send a notice.  Specify message and duration.
def sendNotice(msg, time):
	xbmc.executebuiltin('Notification(' + __plugin__ + ',' + msg + ',' + time +',' + __settings__.getAddonInfo("icon") + ')')


def debug(message):
	message = "ShareThe.TV: " + message
	if (__settings__.getSetting( "debug" ) == 'true'):
		print message


# Query the movie list with JSON
def getMovieLibrary():
	query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "start": 0, "fields": ["title", "year"] }, "id": "1"}'
	return xbmc.executeJSONRPC(query)


# Build out movie XML based on getMovieLibrary() call.  Watch for special chars in title
def buildMovieXML(response):
	match = re.compile('"title" : "(.+?)",\n.+?"year" : (.+?)\n').findall(response)

	movielist = "<movies>"
	for title, year in match:
		movielist += "<movie>"
		movielist += "<title>" + title.replace('&','&amp;') + "</title>"
		movielist += "<year>" + year + "</year>"
		movielist += "</movie>"
	movielist += "</movies>"
	return movielist


# Build out parameters list including user/pass, and movie list
def buildParamsXML(movielist):
	params = "<user>"
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
	# Handle connection refused?
	#except HTTPError, e:
		#sendNotice("Error contacting server, try again soon.", "7000")
	except URLError, e:
		# Success code
		if e.code == 202:
			# Only show notifications if they are enabled in settings
			if (__settings__.getSetting( "notifications" ) == 'true'):
				sendNotice("Library update sent.", "5000")
		elif e.code == 401:
			# Always show error messages, wrong user/pass combo
			sendNotice("Authentication failed.", "5000")
		elif e.code == 403:
			# Refusing to service request because of an empty library
			sendNotice("Empty movie library, not sending update.", "7000")
		else:
			# Unhandled error, maybe all should be handled here
			sendNotice("Unexpected error.", "5000")


# Send a library update to ShareThe.TV
def sendUpdate():
	# Verify username/password entered in settings before continuing
	if (__settings__.getSetting( "email" ) == '' or __settings__.getSetting( "password" ) == ''):
		sendNotice("Configure your account details before submitting.", "6000")
		return
	
	# Build the movie list in XML format
	movielist = buildMovieXML(getMovieLibrary())
	debug('movielist is: ' + movielist)
	
	# Add the movie list to a params list that includes username/password
	params = buildParamsXML(movielist)
	
	sendRequest(params)

# Get the count of movies in the library
def getMovieCount():
	query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "id": "1"}'
	result = xbmc.executeJSONRPC(query)
	match = re.compile('"end" : (.+?),').findall(result)
	return match[0]


def autoStart(option):
	# See if the autoexec.py file exists
	if (os.path.exists(AUTOEXEC_PATH)):
		debug('Found autoexec')
		
		# Var to check if we're in autoexec.py
		found = False
		autoexecfile = file(AUTOEXEC_PATH, 'r')
		filecontents = autoexecfile.readlines()
		autoexecfile.close()
		
		# Check if we're in it
		for line in filecontents:
			if line.find('sharethetv') > 0:
				debug('Found ourselves in autoexec')
				found = True
		
		# If the autoexec.py file is found and we're not in it,
		if (not found and option):
			debug('Adding ourselves to autoexec.py')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			filecontents.append(AUTOEXEC_SCRIPT)
			autoexecfile.writelines(filecontents)            
			autoexecfile.close()
		
		# Found that we're in it and it's time to remove ourselves
		if (found and not option):
			debug('Removing ourselves from autoexec.py')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			for line in filecontents:
				if not line.find('sharethetv') > 0:
					autoexecfile.write(line)
			autoexecfile.close()
	
	else:
		debug('autoexec.py doesnt exist')
		if (os.path.exists(AUTOEXEC_FOLDER_PATH)):
			debug('Creating autoexec.py with our autostart script')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			autoexecfile.write (AUTOEXEC_SCRIPT.strip())
			autoexecfile.close()
		else:
			debug('Scripts folder missing, creating autoexec.py in that new folder with our script')
			os.makedirs(AUTOEXEC_FOLDER_PATH)
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			autoexecfile.write (AUTOEXEC_SCRIPT.strip())
			autoexecfile.close()

# Check if we are executing from startup
startup = False

try:
    count = len(sys.argv) - 1
    if (sys.argv[1] == '-startup'):
        startup = True			
except:
    pass


# Main execution path
autorun = False
if (__settings__.getSetting( "autorun" ) == 'true' ):
	autorun = True

# If triggered from programs menu
if (not startup):
	debug('Triggered from programs menu, setting autostart option and running once')
	# Configure autorun from user setting
	autoStart(autorun)
	
	# Trigger an update
	sendUpdate()
	

oldCount = getMovieCount()

# Stay in busy loop checking for updates and sending updates when needed
if autorun:
	# Busy loop
	debug('Waiting to send updates')
	while 1:
		debug('Checking for library updates')
		
		# Get total count of movies
		newCount = getMovieCount()

		# if the count hasn't changed, wait a bit and check again
		if oldCount == newCount:
			debug('No change in movie count')
			time.sleep(30)
		else:
			# Counts are changing, the library is being updated
			# Let's wait a bit to let the update finish first
			while (oldCount != newCount):
				debug('Change in count found, sleep to let update finish')
				time.sleep(30)
				oldCount = newCount
				newCount = getMovieCount()
			
			# Ok, the counts have stopped changing. Time to send an update
			debug('Counts stopped changing, sending update now')
			sendUpdate()
			time.sleep(30)
		
		# Keep new count as old count for next iteration
		oldCount = newCount

