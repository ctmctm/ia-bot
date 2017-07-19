#!/usr/bin/python3
import xml.etree.ElementTree as ET
import sys 
import tweepy
import random
import time
import datetime
import urllib 
import internetarchive
import itertools
import argparse
import string
import json
import auth

foldoutMode = False
disableTweet = False
offlineMode = False

minMinutes = 42
maxMinutes = 260
sleepSeconds = 2
foldoutChance = 35

parser = argparse.ArgumentParser(description="randomly choose an image from an IA book and tweet it")
group = parser.add_mutually_exclusive_group()
parser.add_argument("searchterm", help="what to search for using IA's advance search -- generally part of an uploader's username")
parser.add_argument("-v", "--verbose", action="store_true", help="display hella feedback")
group.add_argument("-r", "--random", action="store_true", help="gives a %s percent chance of tweeting a foldout, as set by foldoutChance" % (foldoutChance))
group.add_argument("-f", "--foldout", action="store_true", help="tweet a foldout instead of a page")
parser.add_argument("-d", "--disableTweet", action="store_true", help = "run through motions of script but don't actually tweet")
parser.add_argument("-o", "--offline", action="store_true", help = "use existing scandata.xml to test offline components of script")
parser.add_argument("-t", "--timer", action="store_true", help = "will tweet according to other paramters after a random interval between %s and %s mintues" % (minMinutes, maxMinutes))

args = parser.parse_args()
uploader = args.searchterm

if args.verbose:
	def vprint(obj):
		if args.verbose:
			print(obj, end='')
			return
else:
	vprint = lambda *a: None  



def getRandomItem():

#uploader:('christian-mccusker') AND republisher_date:(20170706*)
	
	global search
	try:
		results = len(search)
	except:	
		try:
			if offlineMode == True:
				print('cannot search IA in offline mode')
				sys.exit()
			vprint('searching IA. . . ')
			if foldoutMode == True:
				search_terms = 'uploader:(' + uploader + ') AND foldoutcount:["1" TO "500"]'
			else:
				search_terms = 'uploader:(' + uploader +')'
			search = internetarchive.search_items(search_terms)
			results = len(search)
			vprint ('. . .%d results for \'%s\' \n' % (results, search_terms))
			if results == 0:
				print('No results found for \'%s\'' % (search_terms))
				sys.exit()
		except Exception as e:
			if offlineMode == False:
				print('This script requires a valid IA uploader email address as its first argument.')
			print(e)
			sys.exit()
	id = []
	try:
		x = random.randrange(1, results)
		vprint ('choosing a book at random (%d). . . ' % (x))
		for result in itertools.islice(search, x-1, x, 1):
			randomID = result['identifier']
		vprint ('. . .done!\n')
		return randomID
	except Exception as e:
		print('Failed with error %s' % (e))
		sys.exit()

def getMetadata(id, tag):
	global item
	vprint('getting ' + tag + ' metadata for '+ id + '. . . ')
	item = internetarchive.get_item(id)	
	vprint('. . .done!\n')

	try:
		data = item.metadata[tag]
	except:
		data = ''
	return data
	
	
def downloadFile(identifier, request):
	#e.g., downloadFile(asdf123ff, scandata)
	vprint ('sleeping for %d seconds to lighten load on IA. . . ' % (sleepSeconds))
	time.sleep(sleepSeconds)	
	vprint('. . .ok!\n')
	item = internetarchive.get_item(identifier)
	vprint('downloading file. . . ')
	for file in item.files:
		if request in file['name']:
			download = file['name']
			download = internetarchive.File(item, download)
			download.download(file_path='./files/' + request)
	vprint('. . .done\n')
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
	
	#check if page we're going to post is deleted...
	vprint('Making sure page isn\'t deleted. . . ')
	deleted = getPagetypes('Delete', scanData['root'])
	if leafNumber in deleted:
		vprint('Whoops! Chose a deleted page, starting over...!\n')
		if offlineMode:
			print('Can\'t search IA in offline mode!')
			sys.exit()
		main()
	vprint('. . .ok!\n')
	url = baseURL + leafNumber.zfill(4) + '.jpg'
	vprint('downloading image. . . ')
	urllib.request.urlretrieve(url, "./files/leaf.jpg")
	vprint('. . .downloaded\n')
	return url

def getRandomFoldout(identifier, foldoutList):
	global leafNumber
	baseURL = 'http://archive.org/download/' + identifier + '/' + identifier + '_jp2.zip/' + identifier + '_jp2%2F' + identifier + '_' 
	vprint('. . .%s has %d foldouts\n' % (identifier, len(foldoutList)))
	randomIndex = random.randrange(0, len(foldoutList))
	leafNumber = str(foldoutList[randomIndex])
	url = baseURL + leafNumber.zfill(4) + '.jpg'
	vprint('downloading image. . . ')
	urllib.request.urlretrieve(url, "./files/leaf.jpg")
	vprint('. . .downloaded\n')
	return url

def getPagetypes(pageType, scanData):
	leafnums = []
	for page in scanData.iter('page'):
		pt = page.find('pageType').text	
		if pt == pageType:
			leafNum = page.attrib['leafNum']
			leafnums.append(leafNum)
	return leafnums

## change findFoldouts to getPagetype, have it return 'foldout' or 'deleted' etc
##<pageType>Delete</pageType>
##<pageType>Foldout</pageType>
##<pageType>Normal</pageType>

def anyPage():
	global url
	url = getRandomPage(randomID, scanData['leafCount'])
	postPhoto()

	

def anyFoldout():
	global randomID
	global scanData
	global url
	foldouts = getPagetypes('Foldout', scanData['root'])
	if len(foldouts) == 0:
		vprint('. . .%s has no foldouts' % (randomID))
		print('this code should rarely run--only if running in offline mode on a book w/o foldouts')
		randomID = getRandomItem()
		downloadFile(randomID, 'scandata.xml')
		vprint('checking %s. . . ' % (randomID))
		scanData = parseXML('scandata')
		anyFoldout()
	else:
		url = getRandomFoldout(randomID, foldouts)
		postPhoto()

def generateBookURL(id, leafNumber):
#	generally, the page on the other side of a foldout has an asserted page number
#	if it doesn't, we'll return the details link instead of a 2up link

## split out a getPageNumber function
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


def formatTweet(randomID):
	global leafNumber
	global tweetData
	global tweet
	#generate tweet-friendly title
	full_title = getMetadata(randomID, 'title')
	year = getMetadata(randomID, 'date')
	subjects = getMetadata(randomID, 'subject')
	tweet = ''
	tweet_length = len('From        (year) ') + 24
	title_length = 0
	title = ''
	subject_string = ''
	
	try:
		subjects.split(',')
	except Exception as e:
		vprint (e)
		subjects = subjects
	x = []
	if isinstance(subjects, str):
		subjects = subjects.split()
		
	excludedWords = ['and']
	for subject in subjects:
		if subject in excludedWords:
			continue
		if ' ' in subject and len(subjects) > 1:
			for c in string.punctuation:
				subject = subject.replace(c, '')
			
			x.append('#' + subject.split(' ', 1)[0])
		else:
			x.append('#' + subject)
	
	subjects = list(set(x))
	subject_string = ' '.join(subjects)
	tweet_length += len(subject_string)
	
	t = 0
	title = ' '.join(map(str, title.split()[:t]))
	
	
	for word in full_title:
		if tweet_length + len(word) <= 140:
			title += word
			tweet_length += len(word)
			t += 1
	
	if len(full_title) > t:
		title = title + '...'
	
	
	
	bookURL = ''
	bookURL = generateBookURL(randomID, leafNumber)
	vprint('\n\n' + url + '\n\n')
	tweet = 'From \"' +  title + '\" (' + year +') ' + subject_string + ' \n'
	#url length in a tweet always = 23
	tweet = tweet + bookURL
	vprint(tweet + '\n' + '(' + str(len(tweet)) + ' characters)\n')

def postPhoto():
	global keys
	consumer_secret = keys['consumer_secret']
	consumer_key = keys['consumer_key']
	access_token = keys['access_token']
	access_token_secret = keys['access_token_secret']

	formatTweet(randomID)
	bot_auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	bot_auth.set_access_token(access_token, access_token_secret)
	bot_api = tweepy.API(bot_auth)
	global tweet
	global disableTweet
	if not disableTweet == True:
		vprint('tweeting. . . ')
		try:
			tweetData = bot_api.update_with_media('./files/leaf.jpg', status = tweet)
		except Exception as e:
			print(e)
			print('\n Error  while Tweeting...\n\n')
			#keys = auth.authorize()			
			#postPhoto()
			sys.exit()
		vprint('. . .tweeted tweet id %s!\n\n' % (tweetData.id))
	#sys.exit()

def takeARest():

        x = random.randrange(minMinutes * 60, maxMinutes * 60)
        wakeUpTime = datetime.datetime.now() + datetime.timedelta(seconds=x)
        wakeUpTime = wakeUpTime.strftime(' %I:%M:%S %p')
        print ('next tweet at   |' + str(wakeUpTime) + '')
        print ('(sleeping for ' + str(x//60) + ' minutes)')

        time.sleep(x)
        #print '____________________________'
        print ('__________________________________________________________________________________________________________')

        main()

def postGif():
	global gif
	global randomID 
	gif = True
	downloadFile(randomID, randomID + '.gif')
	postPhoto()

def main():
	global keys
	try:
		keys = auth.getAuthFile()
	except Exception as e:
		print('Authentication error in', sys.argv[0], e)
		sys.exit()



	global gif	
	global randomID
	global foldoutMode
	global scanData
	global disableTweet
	global offlineMode
	global foldouts
	foldoutMode = False
	print(time.strftime('%a %b %m %Y | %I:%M:%S %p'))
	gif = False
	#set foldoutMode to False to have bot tweet out random page instead of random foldout 

	if args.foldout:
		foldoutMode = True
		vprint('foldout mode\n')
	#set disableTweet to True in order to test script w/o sending lots of tweets
	if args.disableTweet:
		disableTweet = True
		vprint('tweeting disabled\n')
	#set offlineMode to True to use previously-download scandata.xml instead of seraching IA
	if args.offline:
		offlineMode = True
		vprint('offline mode\n')

	if args.random:
	        dice = random.randrange(1,100)
	        if dice < foldoutChance:
        	        foldoutMode = True
        	vprint('randomly decided that foldoutMode = %s\n' % (str(foldoutMode)))


	foldouts = []



	if offlineMode == False:
		item = None
		randomID = getRandomItem()
		downloadFile(randomID, 'scandata.xml')
	
	vprint( 'parsing scandata. . . ')
	scanData = parseXML('scandata')
	#next line makes sure we have a value for randomID even if we need to read it from XML
	randomID = scanData['root'][0][0].text
	vprint('. . .done\n')

	if foldoutMode == True:
		vprint('checking %s. . . ' % (randomID))
		anyFoldout()
	else:
		anyPage()
	
	print('\ndone!\n')

	if args.timer:
		takeARest()
	
	
main()
