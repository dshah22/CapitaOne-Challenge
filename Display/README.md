+-------------+
|   _     _   |  IG STAT GRABBER
|  | |___| |  |  Version 1.5
|  |_______|  |
|             |  by Sven Reifschneider <hello@blauesledersofa.de>
+-------------+

IG STAT GRABBER is a open source statistic creator for your instagram profile.
It gets all needed data from the Instagram API saves it in a SQLite database
and visualize everything on a nice html layout.

# Installation
IG STAT GRABBER needs the following (python) libs:
- requests
- jinja2
- sqlite3
- ssl
- python3

This software was tested under python 3.2 on a debian system and works fine.
Install `pip` and after that the following libs (they maybe have different
names on other linux systems than debian / ubuntu / etc.):

	pip-3.2 install requests
	pip-3.2 install jinja2==2.5 (for html template generating)
	
	aptitude install python-dev libffi-dev libssl-dev
	pip-3.2 install pyopenssl ndg-httpsclient pyasn1
	
	aptitude install sqlite3 libsqlite3-dev
	aptitude install python3 python3-pip
	
Please make sure that sqlite3 is installed **before** python so sqlite support
is integrated! `libssl-dev` and so on prevent openssl warnings when connecting
to https pages.

`jinja2.5` is used for html template generating. `requests` for REST-API calls.

If everything is installed you can just execute the script: `./getIGstats.py`

# Configuration
All you need to configure is the `config.ini`. It's already well documented.

## Section IGGrabber:
- dbpath - relative path to the database file. Default value should be fine.
- debuglevel - 0 shows no output, 3 is verbose mode. 
	Modes between show less debug data.
	
## Section Instagram
- access_token - the access token you got from your application
- username - your instagram username

## Section Theme
- html_theme - the folder name of the theme you want use
- tpl_save_dir - path for the processed theme files with all the data.
	This path is relative to the IGGrabber folder.

## Getting an access token
Log into your instagram account and browse to:
https://instagram.com/developer
Click on `Register your application` and fill out the form. If you
already have an application click on `Register a New Client`.

Now you should have a Client ID. Use a Website and Redirect URL of a
website you manage or where you know that nothing could go wrong.

You could use all data for your own application but we don't have a
login page or something like that. So just browse to:
https://api.instagram.com/oauth/authorize/?client_id=CLIENT-ID&redirect_uri=REDIRECT-URI&response_type=code
And fill in your Client ID and the Redirect URI.

You should see a confirmation box that your application wants to access
your account data. Accept it and you should be redirected to your
Redirect URI. Now you should see your access token on your URL in the
browser. Copy it and save it in the `config.ini`. Now we're done and
you're able to use the IG STAT GRABBER!

For more information on the auth process see:
https://instagram.com/developer/authentication/

# Skins
You can use your custom html theme. Just have a look at themes/basic. There
you will find all template files.
Just create your new template in a subfolder in the themes folder.
The value of `html_theme` in the config.ini is just the folder name.

**Attention:** asset files (css / js / etc.) are not copied! So you must
manually copy these files to the htdocs folder!

# Run
IG STAT GRABBER should be executed via cron. An update every 24 hours is
perfect. And follower data should be updated every few days (to prevent API
limits).
An example crontab would be:

	0 9  * * *   user /usr/bin/python3 /path/to/getIGstats.py >> /dev/null 2>&1
	0 15 * * */2 user /usr/bin/python3 /path/to/getIGstats.py follower >> /dev/null 2>&1
	
This would update the database daily at 9am and update the follower data every
second day at 3pm.
	
Run `./getIGstats.py help` for all available commands.
./getIGstats.py follower - only update follower data
./getIGstats.py follows  - only update follows data
./getIGstats.py media    - only update media data
./getIGstats.py stats    - only create stats
./getIGstats.py help     - show help
./getIGstats.py          - executes basic data, follows, media, stats

On **every** run a database backup will be performed. So if something goes wrong, 
just delete the `igstats.db` database and rename `igstats.db_backup` to `igstats.db`

# License
IG STAT GRABBER is licensed under the MIT License. For more informations
see LICENSE.txt.