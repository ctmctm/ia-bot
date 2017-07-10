#!/usr/bin/python

#usage: python random_from_uploader.py username -f -d -o -r
#username can be complete or partial, e.g. christian-mccusker
#-f, -d, -r, and -o each must have a preceding hyphen
# f = foldout mode, -d = debug/disable tweet, -o = use previous scandata, don't query IA, -r = randomly decide whether to choose a foldout or a regular page

import internetarchive, random, sys
import xml.etree.ElementTree as ET
import sys, tweepy, random, time, datetime, urllib

foldoutMode = False
disableTweet = False
offlineMode = False

print(time.strftime('%a %b %m %Y | %I:%M:%S %p'))

#set foldoutMode to False to have bot tweet out random page instead of random foldout 
if '-f' in sys.argv:
	foldoutMode = True
	print 'foldout mode'
#set disableTweet to True in order to test script w/o sending lots of tweets
if '-d' in sys.argv:
	disableTweet = True
	print 'tweeting disabled'
#set offlineMode to True to use previously-download scandata.xml instead of seraching IA
if '-o' in sys.argv:
	offlineMode = True
	print 'offline mode'

if '-r' in sys.argv:
        dice = random.randrange(1,100)
        if dice < 35:
                foldoutMode = True
        print 'randomly decided that foldoutMode = %s' % (str(foldoutMode))


#app keyes
consumer_key = "OCwbAYrqfQQ691x1JKRJadlk4"
consumer_secret = "CkNL7Bl78EmXSo1B8w2Z6siYA3MoqZ6mKXgT4KGY4RKJyKb5gt"

#@ctm user keys
#access_token = "7910542-tKJfPRZ5YVlj5Pcw4aafSuz2NVtax1qLBM4iTtmwrC"
#access_token_secret = "UD8Q7DBVTK7ADSgApxVrM7bASdxmErelTAQLgHYAf0PGJ"

#@ctm_books user keys
access_token = "881249737587830785-ukGDbcJc0donxvs0epzppAmHu9V9b3E"
access_token_secret = "ojhMFeMNyQdAsyqRcOtCV8z164YLiQBoUgTMOKdciB4EG"


bot_auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
bot_auth.set_access_token(access_token, access_token_secret)
bot_api = tweepy.API(bot_auth)
foldouts = []


def getRandomItem():
	global search
	try:
		results = len(search)
	except:	
		try:
			if offlineMode == True:
				print 'cannot search IA in offline mode'
				sys.exit()
			uploader = sys.argv[1]
			print 'searching IA. . .',
			sys.stdout.flush()
			search = internetarchive.search_items('uploader:' + uploader)
			results = len(search)
			print ('. . .%d results' % results)
			if results == 0:
				print "No results found -- this script requires a valid IA uploader email address as its first argument."
				sys.exit()
		except:
			if offlineMode == False:
				print "This script requires a valid IA uploader email address as its first argument."
			sys.exit()
	id = []
	for result in search:
		id.append(result['identifier'])
	randomID = random.choice(id)
	return randomID

def getMetadata(identifier):
	item = internetarchive.get_item(identifier)
	title = item.metadata['title']
	return{'title':title}

def downloadFile(identifier, request):
	#e.g., downloadFile(asdf123ff, scandata)
	item = internetarchive.get_item(identifier)
	print 'downloading file. . .',
	sys.stdout.flush()
	for file in item.files:
		if request in file['name']:
			download = file['name']
			download = internetarchive.File(item, download)

			download.download(file_path='./files/' + request + '.xml')
	print '. . .done'
def parseXML(request):
	#returns leafCount cause thats what this script needs, also returns root XML object to be more versatile
	tree = ET.parse('./files/' + request + '.xml')
	root = tree.getroot()
	leafCount = int(root[0][1].text)
	return{'leafCount':leafCount, 'root':root}
	
def getRandomPage(identifier, leafCount):
	global leafNumber
	baseURL = 'http://archive.org/download/' + identifier + '/' + identifier + '_jp2.zip/' + identifier + '_jp2%2F' + identifier + '_' 
	leafNumber = str(random.randrange(5, leafCount - 4))
	url = baseURL + leafNumber.zfill(4) + '.jpg'
	print 'downloading image. . .',
	sys.stdout.flush()
	urllib.urlretrieve(url, "./files/leaf.jpg")
	print '. . .downloaded'
	return url

def getRandomFoldout(identifier, foldoutList):
	global leafNumber
	baseURL = 'http://archive.org/download/' + identifier + '/' + identifier + '_jp2.zip/' + identifier + '_jp2%2F' + identifier + '_' 
	print '...%s has %d foldouts' % (identifier, len(foldoutList))
	randomIndex = random.randrange(0, len(foldoutList))
	leafNumber = str(foldoutList[randomIndex])
	url = baseURL + leafNumber.zfill(4) + '.jpg'
	print 'downloading image. . .',
	sys.stdout.flush()
	urllib.urlretrieve(url, "./files/leaf.jpg")
	print '. . .downloaded'
	return url

def findFoldouts(scanData):
	for page in scanData.iter('page'):
		pageType = page.find('pageType').text	
		if pageType == "Foldout":
			pageNum = page.attrib['leafNum']
			foldouts.append(pageNum)
	return foldouts

def anyPage():
	global url
	url = getRandomPage(randomID, scanData['leafCount'])
	postPhoto()

def anyFoldout():
	global randomID
	global scanData
	global url
        foldouts = findFoldouts(scanData['root'])
	if len(foldouts) == 0:
		print '. . .%s has no foldouts' % (randomID)
		randomID = getRandomItem()
		downloadFile(randomID, 'scandata')
		print 'checking %s. . .' % (randomID),
		sys.stdout.flush()
		scanData = parseXML('scandata')
		anyFoldout()
	url = getRandomFoldout(randomID, foldouts)
	postPhoto()

def generateBookURL(id, leafNumber):
#	generally, the page on the other side of a foldout has an asserted page number
#	if it doesn't, we'll return the details link instead of a 2up link
	baseURL = 'https://archive.org/stream/' + id 

	for page in scanData['root'].iter('page'):
		if page.attrib['leafNum'] == leafNumber:
			handSide = page.find('handSide').text	
			leafNumber = int(leafNumber)
			if handSide == "RIGHT":
				adjacentLeafNum = leafNumber - 1
			else:
				adjacentLeafNum = leafNumber + 1
			for page in scanData['root'].iter('page'):
				if page.attrib['leafNum'] == str(adjacentLeafNum):
					try:
						pageNum = page.find('pageNumber').text
						bookURL = baseURL + '#page/' + pageNum + '/mode/2up'
					except:
						bookURL = 'http://www.archive.org/details/' + id
					return bookURL

def postPhoto():
        global leafNumber
	#generate tweet-friendly title
	item_metadata = getMetadata(randomID)
	title = item_metadata['title']
	if len(title) > 100:
		title = title[:100] + '...'
	bookURL = generateBookURL(randomID, leafNumber)
	tweet = 'From \"' +  title + '\" ' + bookURL
	print url
	print tweet + "\n"
        global disableTweet
	if not disableTweet == True:
		print 'tweeting. . .',
		sys.stdout.flush()
		bot_api.update_with_media('./files/leaf.jpg', status = tweet)
		print '. . .tweeted'
	sys.exit()


def main():
	global randomID
	global foldoutMode
	if offlineMode == False:
		randomID = getRandomItem()
		downloadFile(randomID, 'scandata')
	global scanData
	print 'parsing scandata. . .',
	sys.stdout.flush()
	scanData = parseXML('scandata')
	print '. . .done'
	#next line makes sure we have a value for randomID even if we need to read it from XML
	randomID = scanData['root'][0][0].text

	if foldoutMode == True:
		print 'checking %s. . .' % (randomID),
		sys.stdout.flush()
		anyFoldout()
	else:
		anyPage()

	print "done!"

main()
