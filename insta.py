
# This file contains the source code for fetching most recent posts from 
# Instagram that contains the #capitalone in the caption of the 
# image. The code also performs a Sentiment Analysis on the caption text 
# indicating the nature of the content of the text towards capitalone. It 
# classifies the text as positive, negative or neutral. The code also find the 
# total number of likes received on the media post. 
# The source also includes the code to get the User details of the post
# including the username, no. of user following, and the number of users 
# followed.
# Pre-requisites: 
#  1. Need a valid access_token from Instagram, client _id, 
#     client_secret key and client_ip. These are usually obtained from the 
#     Instagram developer website. www.instagram.com/developer 
#  2. AlchemyAPI access_token for sentiment analysis that can be obtained from 
#     www.alchemyapi.com

# I am using two different things to get Instagram entities: the 
# python-Instagram library, and also JSON GET requests to demonstrate my use and 
# knowledge of both, keeping in mind the simplicity of the code.

from instagram.client import InstagramAPI
from alchemyapi import AlchemyAPI
import json
import requests
import urllib2

alchemyapi = AlchemyAPI()
client_id = 'XXXXXXXXXXXXXXXXXXX'
client_secret = 'XXXXXXXXXXXXXXXXXXXXXXXX'
access_token = 'XXXXXXXXXXXXXXXXXXXXXXXXXXX'
access_token2 = 'access_token=' + access_token
client_ip = 'XX.XXX.XX.XXX'

#Defining some Colors
GREEN = '\033[92m'
ENDCOLOR = '\033[0m'
RED = '\033[91m'
YELLOW = '\033[93m'
MAGENTA = '\033[95m'

alchemyapi = AlchemyAPI()
api = InstagramAPI(client_id=client_id, client_secret=client_secret, client_ips= client_ip,access_token= access_token) 

# Using python-Instagram library and retrieving recent posts with tag as 
# capitalone
num_posts = 35  # Num of most recent posts to be retrieved
tagged_media, next_ = api.tag_recent_media(num_posts,0,'capitalone')
count = 1
for media in tagged_media:
   print '\n',RED+'Post'+ENDCOLOR, count
   count +=1
   ''' Trying to do sentiment analysis of the image, but as the Instagram database 
    is secure, we do not get access to the private https: URLs
   img_url = media.images['standard_resolution'].url
   img_response = alchemyapi.imageExtraction('url', img_url)
   if img_response['status'] == 'OK':
      print(json.dumps(img_response, indent=4))
   else:
      print('Error in image extraction call: ', img_response['statusInfo'])
   '''
   # Printing the caption of the image and doing sentiment analysis of the 
   # caption targeted towards CapitalOne  
   name = api.user(media.user.id)
   print name
   if hasattr(media, 'caption'): 
             print YELLOW+"Caption :"+ENDCOLOR, media.caption.text

	     response = alchemyapi.sentiment_targeted('text', media.caption.text, 
	     'capital')

	     if response['status'] == 'OK':		  
		  print GREEN+'Sentiment type: '+ENDCOLOR, response['docSentiment']['type']

		  if 'score' in response['docSentiment']:
		     print GREEN + 'Sensitivity Score: '+ENDCOLOR, response['docSentiment']['score']
	     else:
		  print('Error in targeted sentiment analysis call: ',
			response['statusInfo'])
 

   # Printing Media and User Statistics: Media Likes, User Details include 
   # Number of Followers
   # Number of Users Following
   # Total number of User Posts
   print MAGENTA + "Total Media Likes: "+ ENDCOLOR,media.like_count
   
   # Making a JSON GET request and parsing the JSON accordingly
   resp = requests.get('https://api.instagram.com/v1/users/'+ name.id +'/',params=access_token2)
   print MAGENTA + 'User\'s Total posts: '+ENDCOLOR,resp.json()['data']['counts']['media']
   print MAGENTA +'User Followed By: '+ENDCOLOR,resp.json()['data']['counts']['followed_by']
   print MAGENTA +'User Follows: '+ENDCOLOR, resp.json()['data']['counts']['follows']
