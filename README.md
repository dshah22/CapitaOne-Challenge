# CapitalOne - Mindsumo Challenge

This project was developed as a part of the Mindsumo Challenge hosted by CapitalOne as a part of the Software Engineering Summit. The project essentially finds 35 most recent posts from Instagram with #capitalone and displays statistics of the media and the associated user. It also performs a sentiment analysis of the caption targeted towards Capital One.


### Requirements

  - Python libraries: [httplib2](https://pypi.python.org/pypi/httplib2), [json](https://pypi.python.org/pypi/simplejson/),  [requests](http://docs.python-requests.org/en/latest/user/install/#distribute-pip)
  - Python-Instagram Library that can be found [here](https://github.com/Instagram/python-instagram)
  - An ACCESS_TOKEN from [Instagram](https://instagram.com/developer/) to read media and user statistics. 
  - An ACCESS_TOKEN from [AlchemyAPI](www.alchemyapi.com) to generate sentiment analysis.

### Usage
 - Once you have the access tokens, open insta.py and replace the values in following variables with your own values.
`
``` sh 
$ client_id = 'XXXXXXXXXXXX'
$ client_secret = 'XXXXXXXXXXXXX'
$ access_token = 'XXXXXXXXXXXX'
$ client_ip = 'XX.XXX.XX.XXX                                                                   
```  

 - Then open 'api_key.txt' file and place your AlchemyAPI API Key in there. Please do not type anything else in it.
 - To run the script just type 
``` sh 
$ python insta.py
``` 
 - If everything went well, then you should be able see the list of posts followed by the user statistics.
 
### Visual Representation (Optional Deliverable)
   - I tried to create a visual representation of User data, using third-party libraries and modifying it for our purpose. The contents of the Visual Representation are located in the ''Display'' directory. 
 
``` sh
     $ cd Display
 ```
 - Open config.ini file in a text editor of your choice, and insert your ACCESS_TOKEN received from instagram.
 
 ``` sh
     access_token = XXXXXXXXXXXXXXXXX
 ```
  - Then just run the Python script as 
  ```sh
     $ python getIGstat.py
```
 - This will create a database of the user mentioned in the username variable of the config.ini file, and then display the statistics of the User's posts, no. of followers, most likes and comments in a timely manner in a HTML coded web page. Sometimes, when the user has large number of followers/posts, we might get an error and will not be able to see the media, as Instagram limits its API calls to 5000 /hour per access token. To view these :
 ```sh 
     $ cd htdocs 
     $ open index.html
```
 - This will open the webpage in your default Web Browser.
 

### Future Plans

 - Future plans for the project include, creating a visual representation for the statistics of top 30 users who used #capitalone in their posts.
 

### Version
1.0

### Contact
 - Darpan Shah
 - Email: dshah22@umd.edu

