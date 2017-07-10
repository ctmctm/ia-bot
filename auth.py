#!/usr/bin/python3
import tweepy
import json



def getAuthFile():
	try:
		keyfile = open('files/keys').read()
		keys = json.loads(keyfile)
		return keys

	except OSError:
		print('\nPlease authenticate with Twitter\n')
		keys = authorize()
		return keys
        
def authorize():
	generate()
	keys = getAuthFile()
	return keys

def generate():
	keys = {}

	consumer_key = input('Consumer key for App: ')
	consumer_secret = input('Consumer secret for App: ')

	keys['consumer_key'] = consumer_key
	keys['consumer_secret'] = consumer_secret

	app_auth = tweepy.OAuthHandler(consumer_key, consumer_secret)


	try:
		redirect_url = app_auth.get_authorization_url()
	except tweepy.TweepError:
		print('Error! Failed to get request token.')
		getAuthFile()	
	print('Get verifier here:', redirect_url)
	verifier = input('Verifier: ')


	try:
		app_auth.get_access_token(verifier)
	#	ctm_key = ctm_auth.access_token
	#	ctm_secret = ctm_auth.access_token_scret
	except tweepy.TweepError:
		print ('Error! Failed to get access token.')
		getAuthFile()	

	keys['access_token'] = app_auth.access_token
	keys['access_token_secret'] = app_auth.access_token_secret

	#print(keys)	
	with open('files/keys', 'w') as keyfile:
		json.dump(keys, keyfile)
	

