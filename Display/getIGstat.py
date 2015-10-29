#!/usr/bin/env python3

# +-------------+
# |   _     _   |  IG STAT GRABBER
# |  | |___| |  |  Version 1.5
# |  |_______|  |
# |             |  by Sven Reifschneider <hello@blauesledersofa.de>
# +-------------+
#
# --------------------
# Gets all informations from your instagram account
# Makes a list of your followers and creates fancy stats
#
# Requirements:
# pip-3.2 install requests
# pip-3.2 install jinja2==2.5 (for html template generating)
#
# Solution for SSL Warning:
# aptitude install python-dev libffi-dev libssl-dev
# pip-3.2 install pyopenssl ndg-httpsclient pyasn1
#
# General:
# aptitude install sqlite3 libsqlite3-dev (install before installing python so sqlite support is integrated!)
# aptitude install python3 python3-pip
# --------------------

import os
import sys
reload(sys);
sys.setdefaultencoding("utf8")
import traceback
import shutil
import codecs
# For date creating, breaks, etc.
import datetime
import time
# SQLite handling
import sqlite3
# HTTP requests
import requests
# HTML template generator
import jinja2
# Parsing ini-files
import configparser


class IGGrabber:
    # --------------------
    folder = os.path.dirname(os.path.abspath(__file__))
    # Main variables

    # Load from ini
    config = configparser.ConfigParser()
    config.read(folder + '/config.ini')

    # full SQLite-DB path (in current IGGrabber.folder)
    dbpath = folder + "/" + config['IGGrabber']['dbpath']
    # self.debug level: 0 / 1 / 2 / 3 (0 - no output, 3 - much output)
    debuglvl = int(config['IGGrabber']['debuglevel'])

    # Your Instagram Access Token ( https://instagram.com/developer/ )
    ig_access_token = config['Instagram']['access_token']
    ig_username = config['Instagram']['username']

    # The HTML theme you want to use
    html_theme = config['Theme']['html_theme']
    tpl_path = folder + "/themes/" + html_theme

    # The IGGrabber.folder where the generated HTML theme should be saved
    tpl_save_dir = folder + config['Theme']['tpl_save_dir']
    # --------------------

    version = "1.4"

    # Output colors
    # http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    # Constructor
    def __init__(self):
        # INSTAGRAM LIMITS
        # https://instagram.com/developer/limits/
        # We have a token -> Authenticated Calls -> 5,000 / hour per token
        # Counter
        self.ig_calls = 0
        
        # Set self.debug level
        if IGGrabber.debuglvl > 0:
            self.debug = True
        else:
            self.debug = False

        if IGGrabber.debuglvl > 1:
            self.debug2 = True
        else:
            self.debug2 = False

        if IGGrabber.debuglvl > 2:
            self.debug3 = True
        else:
            self.debug3 = False

        print(IGGrabber.ig_username)

        # Init
        try:
            # ---------
            # Let's start
            if self.debug:
                print(IGGrabber.HEADER)
                print("+----------------------+")
                print("|    IG Grabber " + IGGrabber.version + "    |")
                print("+----------------------+")
                print("| Needs Python 3.2+    |")
                print("| Possible parameters: |")
                print("|   follower | media   |")
                print("|    follows | stats   |")
                print("|   or empty for all!  |")
                print("+----------------------+")
                print("| Have fun, good shots |")
                print("|    and a nice day!   |")
                print("+----------------------+")
                print(IGGrabber.ENDC)

            # Create database if not existing
            if not os.path.exists(IGGrabber.dbpath):
                open(IGGrabber.dbpath, 'w').close()

            # Make backup of current database and remove old backup
            dbbackuppath = IGGrabber.folder + "/igstats.db_backup"
            try:
                os.remove(dbbackuppath)
            except OSError:
                pass

            # Make backup (copy database)
            try:
                shutil.copy(IGGrabber.dbpath, dbbackuppath)
            except IOError as e:
                print(IGGrabber.FAIL + 'Error while creating backup: %s' + IGGrabber.ENDC % e.strerror)

            if self.debug2:
                print(IGGrabber.OKBLUE + "Database backup successful." + IGGrabber.ENDC)

            # Start SQLite
            self.conn = sqlite3.connect(IGGrabber.dbpath)
            self.c = self.conn.cursor()

            # Create tables on first run (when they don't exist)
            # The user who will be analyzed
            # One row per day (for stats etc.) (date of value is in "History")
            self.c.execute('''CREATE TABLE IF NOT EXISTS User(
                ID INTEGER PRIMARY KEY,
                Username VARCHAR(80),
                IG_ID VARCHAR(20),
                Media INT,
                Followers INT,
                Following INT,
                Bio TEXT,
                ProfilePicURL VARCHAR(200),
                History DATE)''')

            # Every follower you ever had (since analyzing)
            self.c.execute('''CREATE TABLE IF NOT EXISTS Followers (
                IG_ID VARCHAR(20) PRIMARY KEY,
                Username VARCHAR(80),
                FullName VARCHAR(150),
                ProfilePicURL VARCHAR(200),
                Following INT,
                Followers INT,
                Media INT,
                Bio TEXT,
                FirstSeen DATE,
                LastSeen DATE)''')

            # Accounts you follow
            self.c.execute('''CREATE TABLE IF NOT EXISTS Following (
                IG_ID VARCHAR(20) PRIMARY KEY,
                Username VARCHAR(80),
                FullName VARCHAR(150),
                ProfilePicURL VARCHAR(200),
                FirstSeen DATE,
                LastSeen DATE)''')

            # User with changed usernames
            self.c.execute('''CREATE TABLE IF NOT EXISTS NameChanges (
                IG_ID VARCHAR(20) PRIMARY KEY,
                UsernameOld VARCHAR(80),
                UsernameNew VARCHAR(80),
                Changed DATE)''')

            # Your media
            self.c.execute('''CREATE TABLE IF NOT EXISTS Media (
                ID VARCHAR(40) PRIMARY KEY,
                Created DATETIME,
                Filter VARCHAR(30),
                Link VARCHAR(80),
                Location VARCHAR(100),
                Likes INT,
                Comments INT,
                ImageURL VARCHAR(200),
                Descr TEXT,
                Type VARCHAR(20))''')

            # Your used tags
            self.c.execute('''CREATE TABLE IF NOT EXISTS Tags (
                Name VARCHAR(100) PRIMARY KEY,
                Qty INT,
                LastUsed DATE)''')

            # Users who like your media
            self.c.execute('''CREATE TABLE IF NOT EXISTS Likers (
                IG_ID VARCHAR(20) PRIMARY KEY,
                Username VARCHAR(80),
                FullName VARCHAR(150),
                LastLike DATE)''')

            # Liker <-> your media
            self.c.execute('''CREATE TABLE IF NOT EXISTS Likers_Media (
                Liker VARCHAR(20),
                Media VARCHAR(40),
                Created DATE,
                PRIMARY KEY(Liker, Media))''')

            # All comments
            self.c.execute('''CREATE TABLE IF NOT EXISTS Comments (
                ID VARCHAR(40) PRIMARY KEY,
                IG_ID VARCHAR(20),
                Username VARCHAR(80),
                FullName VARCHAR(150),
                ProfilePicURL VARCHAR(200),
                Created DATETIME,
                Content TEXT)''')

            # People who interact with you but don't follow you
            self.c.execute('''CREATE TABLE IF NOT EXISTS MiscPeople (
                IG_ID VARCHAR(20) PRIMARY KEY,
                Username VARCHAR(80),
                FullName VARCHAR(150))''')
            
            # Get current date for db values
            self.today_raw = datetime.date.today()
            self.today = self.today_raw.strftime("%Y-%m-%d")

        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)

    # --- END INIT
    
    # Get user information
    def userinfo(self):
        try:
            # Get User ID (if not saved get all data from the IG server)
            have_user_id = False
            for row in self.c.execute("SELECT IG_ID FROM User WHERE Username=?", (IGGrabber.ig_username,)):
                have_user_id = True
                #ig_id = str(row[0])
		ig_id = '578045120'

            if not have_user_id:
                # Get User ID
                if self.debug:
                    print(IGGrabber.WARNING + "User ID not found, I'll get it from instagram" + IGGrabber.ENDC)

                payload = {'access_token': IGGrabber.ig_access_token, 'q': IGGrabber.ig_username}
                r = requests.get('https://api.instagram.com/v1/users/search', params=payload)
                data = r.json()
                self.ig_calls += 1  # We made a call!

                for row in data['data']:
                    have_user_id = True
                    #ig_id = row['id']
		    ig_id = '578045120'

                # We got it!
                if self.debug:
                    print(IGGrabber.OKBLUE + "User ID found: " + ig_id + IGGrabber.ENDC)

            # If we still don't have the User ID -> exit!
            if not have_user_id:
                print(IGGrabber.FAIL + "User ID still not found. Check username or your API access!"
                      + ig_id + IGGrabber.ENDC)
                sys.exit(0)

            self.ig_id = ig_id
	    print 'ig_id: ', ig_id

            # ----------
            # Get account informations and save them
            if self.debug:
                print("")
                print(IGGrabber.HEADER + "Getting account informations" + IGGrabber.ENDC)

            payload = {'access_token': IGGrabber.ig_access_token}
            r = requests.get('https://api.instagram.com/v1/users/' + self.ig_id + '/', params=payload)
	    print 'response Status Check: ',r
	    data = r.json()
            self.ig_calls += 1  # We made a call!
	    print self
            self.username = data['data']['username']
            self.bio = data['data']['bio']
            self.media = data['data']['counts']['media']
            self.follower = data['data']['counts']['followed_by']
            self.follows = data['data']['counts']['follows']
            self.picurl = data['data']['profile_picture']

            if self.debug:
                print(IGGrabber.OKBLUE + "Got data: username: " + self.username + ", " + str(self.follower)
                      + " followers, " + str(self.follows) + " following" + IGGrabber.ENDC)

            # Save values if we have no data from self.today in our database
            self.c.execute("SELECT ID FROM User WHERE History=?", (self.today,))
            if self.c.fetchone() is None:
                if self.debug:
                    print(IGGrabber.WARNING + "No record in database from today - Inserting new row" + IGGrabber.ENDC)
                self.c.execute(
                    "INSERT INTO User (Username, IG_ID, Media, Followers, Following, Bio, ProfilePicURL, History) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    (self.username, ig_id, self.media, self.follower, self.follows, self.bio, self.picurl, self.today))
                
        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)                

    # Main function (do everything!)
    def main(self):
        try:
            # Get user information
            self.userinfo()

            # Update followers etc.
            self.updatefollowerdata(False)

            # Update following list
            self.updatefollowingdata()

            # Media stats
            self.updatemediadata()

            # HTML stats
            self.htmlstats()

            # Output stats
            self.outputstats()

        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)

        # Disconnect from database and exit
        self.conn.commit()
        self.conn.close()
        sys.exit(0)

    # --- END MAIN

    # Update follower informations
    def updatefollowerdata(self, fullupdate):
        try:
            # ----------
            # Get followers
            if self.debug:
                print("")
                print(IGGrabber.HEADER + "Getting follower informations" + IGGrabber.ENDC)

            try:
                ig_id = self.ig_id
            except AttributeError:
                # Not set -> get the information...
                self.userinfo()
                ig_id = self.ig_id

            # We collect followers as long as we have a next_cursor
            has_next_cursor = True
            f_count = 0
            self.f_newfollower = 0
            while has_next_cursor:
                # If we have 0 followers, we have no next_cursor!
                if f_count == 0:
                    payload = {'access_token': IGGrabber.ig_access_token}
                    r = requests.get('https://api.instagram.com/v1/users/' + ig_id + '/followed-by',
                                     params=payload)
                else:
                    # We got the next URL to continue our journey
                    r = requests.get(next_url)

                data = r.json()
                self.ig_calls += 1  # We made a call!

                # If we have a next cursor we have work
                try:
                    # Collect followers
                    for row in data['data']:
                        f_username = row['username']
                        f_picurl = row['profile_picture']
                        f_name = row['full_name']
                        f_id = row['id']

                        # Increase counter
                        f_count += 1

                        # Check if user exists
                        self.c.execute("SELECT IG_ID FROM Followers WHERE IG_ID=?", (f_id,))
                        if self.c.fetchone() is None:
                            print(IGGrabber.OKBLUE + "Getting custom follower informations" + IGGrabber.ENDC)
                            # Insert
                            # Get custom information
                            payload = {'access_token': IGGrabber.ig_access_token}
                            r1 = requests.get('https://api.instagram.com/v1/users/' + f_id, params=payload)
                            data1 = r1.json()
                            self.ig_calls += 1  # We made a call!

                            # Are we allowed?
                            if data1['meta']['code'] == 200:
                                f_followers = data1['data']['counts']['followed_by']
                                f_follows = data1['data']['counts']['follows']
                                f_media = data1['data']['counts']['media']
                                f_bio = data1['data']['bio']
                            else:
                                if self.debug3:
                                    print(IGGrabber.WARNING + "Instagram forbids us to learn more about this person :("
                                          + IGGrabber.ENDC)
                                f_followers = 0
                                f_follows = 0
                                f_media = 0
                                f_bio = ""

                            # SQL Insert
                            self.c.execute(
                                "INSERT INTO Followers (IG_ID, Username, FullName, ProfilePicURL, Following, "
                                "Followers, Media, Bio, FirstSeen, LastSeen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                                (f_id, f_username, f_name, f_picurl, f_follows, f_followers, f_media, f_bio, self.today,
                                 self.today))
                            self.f_newfollower += 1
                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(f_count) + " - Found new user: " + f_username
                                      + IGGrabber.ENDC)
                        else:
                            # Update

                            # Get current username
                            for row1 in self.c.execute("SELECT Username FROM Followers WHERE IG_ID=?", (f_id,)):
                                oldusername = str(row1[0])
                                
                            # Get custom information if we should
                            if fullupdate:
                                payload = {'access_token': IGGrabber.ig_access_token}
                                r1 = requests.get('https://api.instagram.com/v1/users/' + f_id, params=payload)
                                data1 = r1.json()
                                self.ig_calls += 1  # We made a call!
    
                                # Are we allowed?
                                if data1['meta']['code'] == 200:
                                    f_followers = data1['data']['counts']['followed_by']
                                    f_follows = data1['data']['counts']['follows']
                                    f_media = data1['data']['counts']['media']
                                    f_bio = data1['data']['bio']
                                else:
                                    if self.debug3:
                                        print(IGGrabber.WARNING 
                                              + "Instagram forbids us to learn more about this person :("
                                              + IGGrabber.ENDC)
                                    f_followers = 0
                                    f_follows = 0
                                    f_media = 0
                                    f_bio = ""
    
                                self.c.execute(
                                    "UPDATE Followers SET Username=?, FullName=?, ProfilePicURL=?, "
                                    "Following=?, Followers=?, Media=?, Bio=?, LastSeen=? WHERE IG_ID=?",
                                    (f_username, f_name, f_picurl, f_follows, 
                                     f_followers, f_media, f_bio, self.today, f_id)
                                )
                            else:
                                # No full update, just updating normal data without extra call
                                self.c.execute(
                                    "UPDATE Followers SET Username=?, FullName=?, "
                                    "ProfilePicURL=?, LastSeen=? WHERE IG_ID=?",
                                    (f_username, f_name, f_picurl, self.today, f_id)
                                )
                            
                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(f_count) + " - Found existing user: " + f_username
                                      + IGGrabber.ENDC)

                            # Check if username changed
                            if oldusername != f_username:
                                # Username changed!
                                if self.debug3:
                                    print(IGGrabber.WARNING + str(f_count) + " - Username changed!"
                                          + IGGrabber.ENDC)
                                self.c.execute("INSERT INTO NameChanges (IG_ID, UsernameOld, UsernameNew, Changed) "
                                               "VALUES (?,?,?,?)",
                                               (f_id, oldusername, f_username, self.today))

                    # Finished current loop
                    if self.debug:
                        print(IGGrabber.WARNING +
                              "Finished current loop! Starting next round! Followers processed: "
                              + str(f_count) + IGGrabber.ENDC)

                    # Our next URL we have to work on
                    next_cursor = data['pagination']['next_cursor']
                    next_url = data['pagination']['next_url']
                    if self.debug2:
                        print(IGGrabber.WARNING + "Next cursor: " + next_cursor + IGGrabber.ENDC)
                        print("")

                    # Short break
                    if self.debug:
                        time.sleep(0.2)

                # Finished full loop - no more next_cursor!
                except KeyError:
                    if self.debug:
                        print("")
                        print(IGGrabber.HEADER + "Finished loop! Followers: " + str(f_count) + " (" + str(
                            self.f_newfollower) + " new)" + IGGrabber.ENDC)
                    break

            # --- ENDWHILE

            # Check if we processed them all
            if self.debug:
                if self.follower != f_count:
                    print(IGGrabber.FAIL + "ERROR! Your followers: " + str(self.follower) + ", processed: " + str(
                        f_count) + IGGrabber.ENDC)
                else:
                    print(IGGrabber.WARNING + "Processed all followers. Everything alright!" + IGGrabber.ENDC)

            # Commit all!
            self.conn.commit()

        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)

    # --- END updatefollowerdata

    # Update following informations
    def updatefollowingdata(self):
        try:
            # ----------
            # Get followings
            if self.debug:
                print("")
                print(IGGrabber.HEADER + "Getting following informations" + IGGrabber.ENDC)

            try:
                ig_id = self.ig_id
            except AttributeError:
                # Not set -> get the information...
                self.userinfo()
                ig_id = self.ig_id

            # We collect followers as long as we have a next_cursor
            has_next_cursor = True
            fw_count = 0
            self.f_newfollowing = 0
            while has_next_cursor:
                # If we have 0 followers, we have no next_cursor!
                if fw_count == 0:
                    payload = {'access_token': IGGrabber.ig_access_token}
                    r = requests.get('https://api.instagram.com/v1/users/' + ig_id + '/follows',
                                     params=payload)
                else:
                    # We got the next URL to continue our journey
                    r = requests.get(next_url)

                data = r.json()
                self.ig_calls += 1  # We made a call!

                # If we have a next cursor we have work
                try:
                    # Collect followers
                    for row in data['data']:
                        f_username = row['username']
                        f_picurl = row['profile_picture']
                        f_name = row['full_name']
                        f_id = row['id']

                        # Increase counter
                        fw_count += 1

                        # Check if user exists
                        self.c.execute("SELECT IG_ID FROM Following WHERE IG_ID=?", (f_id,))
                        if self.c.fetchone() is None:
                            # SQL Insert
                            self.c.execute(
                                "INSERT INTO Following (IG_ID, Username, FullName, ProfilePicURL, FirstSeen, LastSeen) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (f_id, f_username, f_name, f_picurl, self.today, self.today))
                            self.f_newfollowing += 1
                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(fw_count) + " - Found new user: " + f_username
                                      + ", ID: " + f_id + IGGrabber.ENDC)
                        else:
                            # Update
                            self.c.execute(
                                "UPDATE Following SET Username=?, FullName=?, "
                                "ProfilePicURL=?, LastSeen=? WHERE IG_ID=?",
                                (f_username, f_name, f_picurl, self.today, f_id)
                            )

                            # Get current username
                            for row1 in self.c.execute("SELECT Username FROM Following WHERE IG_ID=?", (f_id,)):
                                oldusername = str(row1[0])

                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(fw_count) + " - Found existing user: " + f_username
                                      + IGGrabber.ENDC)

                            # Check if username changed
                            if oldusername != f_username:
                                # Username changed!
                                if self.debug3:
                                    print(IGGrabber.WARNING + str(fw_count) + " - Username changed!"
                                          + IGGrabber.ENDC)

                                # Only insert if not already existing!
                                self.c.execute("SELECT IG_ID FROM NameChanges WHERE UsernameOld=? AND UsernameNEW=?",
                                               (oldusername, f_username))
                                if self.c.fetchone() is None:
                                    self.c.execute("INSERT INTO NameChanges (IG_ID, UsernameOld, UsernameNew, Changed) "
                                                   "VALUES (?,?,?,?)", (f_id, oldusername, f_username, self.today))

                    # Finished current loop
                    if self.debug:
                        print(IGGrabber.WARNING +
                              "Finished current loop! Starting next round! Following processed: "
                              + str(fw_count) + IGGrabber.ENDC)

                    # Our next URL we have to work on
                    next_cursor = data['pagination']['next_cursor']
                    next_url = data['pagination']['next_url']
                    if self.debug2:
                        print(IGGrabber.WARNING + "Next cursor: " + next_cursor + IGGrabber.ENDC)
                        print("")

                    # Short break
                    if self.debug:
                        time.sleep(0.2)

                # Finished full loop - no more next_cursor!
                except KeyError:
                    if self.debug:
                        print("")
                        print(IGGrabber.HEADER + "Finished loop! Follows: " + str(fw_count) + " (" + str(
                            self.f_newfollowing) + " new)" + IGGrabber.ENDC)
                    break

            # --- ENDWHILE

            # Check if we processed them all
            if self.debug:
                if self.follows != fw_count:
                    print(IGGrabber.FAIL + "ERROR! You follow: " + str(self.follower) + ", processed: " + str(
                        fw_count) + IGGrabber.ENDC)
                else:
                    print(IGGrabber.WARNING + "Processed all follows. Everything alright!" + IGGrabber.ENDC)

            # Commit all!
            self.conn.commit()

        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)
    # --- END updatefollowingdata
    
    def updatemediadata(self):
        try:
            # ----------
            # Media stats
            if self.debug:
                print("")
                print(IGGrabber.HEADER + "Getting media informations" + IGGrabber.ENDC)
                
            try:
                ig_id = self.ig_id
            except AttributeError:
                # Not set -> get the information...
                self.userinfo()
                ig_id = self.ig_id
            
            # We collect media as long as we have a next_cursor (same as above with followers)
            has_next_media = True
            self.m_count = 0
            self.m_new_likes = 0
            self.m_new_comments = 0
            while has_next_media:
                # If we have 0 followers, we have no next_cursor!
                if self.m_count == 0:
                    payload = {'access_token': IGGrabber.ig_access_token}
                    r = requests.get('https://api.instagram.com/v1/users/' + ig_id + '/media/recent',
                                     params=payload)
                else:
                    # We got the next URL to continue our journey
                    r = requests.get(next_url)

                data = r.json()
                self.ig_calls += 1  # We made a call!

                # If we have a next cursor we have work
                try:
                    # Collect media
                    for row in data['data']:

                        m_id = row['id']
                        m_type = row['type']
                        m_tags = row['tags']
                        m_comments = row['comments']['count']
                        m_comments_data = row['comments']['data']
                        m_likes = row['likes']['count']
                        m_likes_data = row['likes']['data']
                        m_filter = row['filter']
                        m_created = row['created_time']
                        m_link = row['link']
                        m_picurl = row['images']['low_resolution']['url']  # thumbnail, same for videos!

                        # Caption can be none!
                        if row['caption'] is None:
                            m_descr = ""
                        else:
                            m_descr = row['caption']['text']

                        # Location can be none if nothing is set!
                        if row['location'] is None:
                            m_location = ""
                        else:
                            if 'name' in row['location']:
                                m_location = row['location']['name']
                            else:
                                m_location = ""

                        m_date = datetime.datetime.fromtimestamp(int(m_created)).strftime('%Y-%m-%d %H:%M:%S')

                        # Increase counter
                        self.m_count += 1

                        # Check if media exists
                        self.c.execute("SELECT ID FROM Media WHERE ID=?", (m_id,))
                        if self.c.fetchone() is None:
                            # Insert
                            self.c.execute("INSERT INTO Media (ID, Created, Filter, Link, Location, Likes, "
                                           "Comments, ImageURL, Descr, Type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                                (m_id, m_date, m_filter, m_link, m_location, m_likes, m_comments, m_picurl, m_descr,
                                 m_type))

                            # Insert hashtags
                            for row1 in m_tags:
                                self.c.execute("SELECT Qty FROM Tags WHERE Name=?", (row1,))
                                if self.c.fetchone() is None:
                                    # Insert hashtag
                                    self.c.execute("INSERT INTO Tags (Name, Qty, LastUsed) VALUES (?,?,?)",
                                                   (row1, "1", self.today))
                                else:
                                    # Update hashtag
                                    self.c.execute("UPDATE Tags SET Qty = Qty + 1, LastUsed=? WHERE Name=?",
                                                   (self.today, row1))

                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(self.m_count) + " - Found new media from: " + m_date
                                      + IGGrabber.ENDC)
                        else:
                            # Update
                            self.c.execute("UPDATE Media SET Likes=?, Comments=?, Descr=? WHERE ID=?",
                                           (m_likes, m_comments, m_descr, m_id))
                            if self.debug3:
                                print(IGGrabber.OKBLUE + str(self.m_count) + " - Found existing media from: " + m_date
                                      + IGGrabber.ENDC)

                        # -----
                        # Update likes
                        if self.debug2:
                            print(IGGrabber.OKBLUE + str(self.m_count) + " - Update likers..." + IGGrabber.ENDC)
                        for row1 in m_likes_data:
                            liker = row1["id"]
                            liker_name = row1['full_name']
                            liker_user = row1['username']

                            # Look if this like is in our database
                            self.c.execute("SELECT * FROM Likers_Media WHERE Liker=? AND Media=?", (liker, m_id))
                            if self.c.fetchone() is None:
                                # Like isn't in our database -> insert!
                                self.m_new_likes += 1
                                self.c.execute("INSERT INTO Likers_Media (Liker, Media, Created) VALUES (?,?,?)",
                                               (liker, m_id, self.today))

                            # Look if this liker is in our database
                            self.c.execute("SELECT * FROM Likers WHERE IG_ID=?", (liker,))
                            if self.c.fetchone() is None:
                                # Liker isn't in our database -> insert!
                                self.c.execute(
                                    "INSERT INTO Likers (IG_ID, Username, FullName, LastLike) VALUES (?,?,?,?)",
                                    (liker, liker_user, liker_name, self.today))
                            else:
                                # Liker is in our database -> update!
                                self.c.execute("UPDATE Likers SET LastLike=?, Username=?, FullName=? WHERE IG_ID=?",
                                               (self.today, liker_user, liker_name, liker))

                        # -----
                        # Update comments
                        if self.debug2:
                            print(IGGrabber.OKBLUE + str(self.m_count) + " - Update comments..." + IGGrabber.ENDC)
                        for row1 in m_comments_data:
                            c_created = row1['created_time']
                            c_content = row1['text']
                            c_id = row1['id']
                            c_userid = row1['from']['id']
                            c_username = row1['from']['username']
                            c_fullname = row1['from']['full_name']
                            c_picurl = row1['from']['profile_picture']

                            c_date = datetime.datetime.fromtimestamp(int(c_created)).strftime('%Y-%m-%d %H:%M:%S')

                            # Look if comment is in our database
                            self.c.execute("SELECT ID FROM Comments WHERE ID=?", (c_id,))
                            if self.c.fetchone() is None:
                                # Insert!
                                self.m_new_comments += 1
                                self.c.execute("INSERT INTO Comments (ID, IG_ID, Username, FullName, "
                                               "ProfilePicURL, Created, Content) VALUES (?,?,?,?,?,?,?)",
                                    (c_id, c_userid, c_username, c_fullname, c_picurl, c_date, c_content))
                            else:
                                # Update comment
                                self.c.execute(
                                    "UPDATE Comments SET Content=?, Username=?, FullName=?, ProfilePicURL=? WHERE ID=?",
                                    (c_content, c_username, c_fullname, c_picurl, c_id))

                    # Finished current loop
                    if self.debug:
                        print(IGGrabber.WARNING + "Finished current loop! Starting next round! Media processed: "
                              + str(self.m_count) + IGGrabber.ENDC)

                    # Our next URL we have to work on
                    next_max_id = data['pagination']['next_max_id']
                    next_url = data['pagination']['next_url']
                    if self.debug2:
                        print(IGGrabber.WARNING + "Next max ID: " + next_max_id + IGGrabber.ENDC)
                        print("")

                    # Short break
                    if self.debug:
                        time.sleep(0.5)

                # Finished full loop - no more next_cursor!
                except KeyError:
                    if self.debug:
                        print("")
                        print(IGGrabber.HEADER + "Finished loop! Media: " + str(self.m_count) + " (" + str(
                            self.m_new_likes) + " new likes, " + str(self.m_new_comments) + " new comments)"
                              + IGGrabber.ENDC)
                    break

            # --- ENDWHILE

            # Check if we processed them all
            if self.debug:
                if self.media != self.m_count:
                    print(IGGrabber.FAIL + "ERROR! Your media: " + str(self.media) + ", processed: "
                          + str(self.m_count) + IGGrabber.ENDC)
                else:
                    print(IGGrabber.WARNING + "Processed all media. Everything alright!" + IGGrabber.ENDC)

            # Commit all!
            self.conn.commit()
                    
        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)

    # --- END updatemediadata                    

    def htmlstats(self):
        try:
            # ----------
            # HTML Stats
            if self.debug:
                print(IGGrabber.HEADER + "Creating HTML Stats" + IGGrabber.ENDC)

            try:
                media = self.media
                follower = self.follower
                follows = self.follows
                username = self.username
            except AttributeError:
                # Not set -> get the information...
                self.userinfo()
                media = self.media
                follower = self.follower
                follows = self.follows
                username = self.username

            # -----
            # Create all the stats!
            for typ in ['Daily', 'Weekly', 'Monthly', 'Yearly', 'All']:

                if typ == "Daily":
                    if self.debug:
                        print(IGGrabber.WARNING + "Creating daily stats" + IGGrabber.ENDC)
                    templatefile = "index.html"
                    tpl_title = "Today - IG Stats - " + username
                    tpl_descr = "Daily stats for Instagram account " + username
                    tpl_timedelta = 1

                elif typ == "Weekly":
                    if self.debug:
                        print(IGGrabber.WARNING + "Creating weekly stats" + IGGrabber.ENDC)
                    templatefile = "week.html"
                    tpl_title = "Week - IG Stats - " + username
                    tpl_descr = "Weekly stats for Instagram account " + username
                    tpl_timedelta = 7

                elif typ == "Monthly":
                    if self.debug:
                        print(IGGrabber.WARNING + "Creating monthly stats" + IGGrabber.ENDC)
                    templatefile = "month.html"
                    tpl_title = "Month - IG Stats - " + username
                    tpl_descr = "Monthly stats for Instagram account " + username
                    tpl_timedelta = 28

                elif typ == "Yearly":
                    if self.debug:
                        print(IGGrabber.WARNING + "Creating yearly stats" + IGGrabber.ENDC)
                    templatefile = "year.html"
                    tpl_title = "Year - IG Stats - " + username
                    tpl_descr = "Yearly stats for Instagram account " + username
                    tpl_timedelta = 365

                elif typ == "All":
                    if self.debug:
                        print(IGGrabber.WARNING + "Creating overall stats" + IGGrabber.ENDC)
                    templatefile = "all.html"
                    tpl_title = "Overall - IG Stats - " + username
                    tpl_descr = "Overall stats for Instagram account " + username
                    tpl_timedelta = 3650  # 10 years, should be enough!

                tpl_vars = dict()
                tpl_vars['title'] = tpl_title
                tpl_vars['description'] = tpl_descr
                tpl_vars['u_username'] = username

                # Dates
                tpl_vars['gentime'] = time.strftime("%d.%m.%Y %H:%M:%S")

                # Yesterday
                y_raw = datetime.date.today() - datetime.timedelta(days=1)
                yesterday = y_raw.strftime("%Y-%m-%d")

                # Since date
                since_raw = datetime.date.today() - datetime.timedelta(days=tpl_timedelta)
                since_date = since_raw.strftime("%Y-%m-%d")
                # Don't show date for overall stats
                if tpl_timedelta == 3650:
                    tpl_vars['since_nice'] = "beginning"
                else:
                    tpl_vars['since_nice'] = since_raw.strftime("%d.%m.%Y")

                # Follow facts
                tpl_vars['followers'] = follower
                tpl_vars['following'] = follows
                tpl_vars['postcount'] = media

                # Ignore the first date because it was init!
                self.c.execute("SELECT History FROM User ORDER BY History ASC LIMIT 0,1")
                firstrowdate = self.c.fetchone()[0]

                # New and lost follower + count
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get new and lost follower" + IGGrabber.ENDC)

                self.c.execute("SELECT Username, ProfilePicURL FROM Followers "
                               "WHERE (FirstSeen BETWEEN ? AND ?) AND (FirstSeen IS NOT ?)",
                               (since_date, self.today, firstrowdate))
                rows = self.c.fetchall()

                new_follower_count = len(rows)
                tpl_vars['new_follower_count'] = new_follower_count
                # List
                if rows is None or len(rows) > 60:
                    tpl_vars['new_follower_list'] = ""
                else:
                    tpl_vars['new_follower_list'] = rows

                self.c.execute("SELECT Username, ProfilePicURL FROM Followers WHERE LastSeen BETWEEN ? AND ?",
                               (since_date, yesterday))
                rows = self.c.fetchall()
                lost_follower_count = len(rows)
                tpl_vars['lost_follower_count'] = lost_follower_count
                # List
                if rows is None or len(rows) > 60:
                    tpl_vars['lost_follower_list'] = ""
                else:
                    tpl_vars['lost_follower_list'] = rows

                # Follow difference
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get follower difference" + IGGrabber.ENDC)

                self.c.execute("SELECT Media, Followers, Following FROM User "
                               "WHERE (History BETWEEN ? AND ?) AND (History IS NOT ?) ORDER BY History ASC LIMIT 0,1",
                               (since_date, self.today, firstrowdate))
                rows = self.c.fetchall()
                if rows is None:
                    tpl_vars['follower_diff'] = 0
                    tpl_vars['following_diff'] = 0
                    tpl_vars['post_diff'] = 0
                else:
                    for row in rows:
                        # Also add an + if value is positive!
                        fer_diff = new_follower_count - lost_follower_count
                        fng_diff = follows - int(row[2])
                        pst_diff = media - int(row[0])

                        if fer_diff > 0:
                            tpl_vars['follower_diff'] = "+" + str(fer_diff)
                        else:
                            tpl_vars['follower_diff'] = str(fer_diff)

                        if fng_diff > 0:
                            tpl_vars['following_diff'] = "+" + str(fng_diff)
                        else:
                            tpl_vars['following_diff'] = str(fng_diff)

                        if pst_diff > 0:
                            tpl_vars['post_diff'] = "+" + str(pst_diff)
                        else:
                            tpl_vars['post_diff'] = str(pst_diff)

                # Values for charts
                # Year as label only when chart is for yearly or overall
                if typ == "Yearly" or typ == "All":
                    self.c.execute("SELECT Followers, strftime('%d.%m.%Y', History) as Date "
                                   "FROM User WHERE History BETWEEN ? AND ?", (since_date, self.today))
                else:
                    self.c.execute("SELECT Followers, strftime('%d.%m', History) as Date "
                                   "FROM User WHERE History BETWEEN ? AND ?", (since_date, self.today))

                rows = self.c.fetchall()
                chart_followers = list()
                for row in rows:
                    chart_followers.append([row[1], row[0]])
                tpl_vars['chart_followers'] = chart_followers

                # Same for following
                if typ == "Yearly" or typ == "All":
                    self.c.execute("SELECT Following, strftime('%d.%m.%Y', History) as Date "
                                   "FROM User WHERE History BETWEEN ? AND ?", (since_date, self.today))
                else:
                    self.c.execute("SELECT Following, strftime('%d.%m', History) as Date "
                                   "FROM User WHERE History BETWEEN ? AND ?", (since_date, self.today))
                rows = self.c.fetchall()
                chart_following = list()
                for row in rows:
                    chart_following.append([row[1], row[0]])
                tpl_vars['chart_following'] = chart_following

                # Most likes
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get posts with most likes" + IGGrabber.ENDC)

                self.c.execute("SELECT COUNT(*) AS Qty, Liker FROM Likers_Media WHERE (Created BETWEEN ? AND ?) "
                               "AND (Created IS NOT ?) GROUP BY Liker ORDER BY Qty DESC LIMIT 0,10",
                               (since_date, self.today, firstrowdate))
                rows = self.c.fetchall()
                if rows is None:
                    tpl_vars['most_likers'] = ""
                else:
                    l = list()
                    for row in rows:
                        self.c.execute("SELECT Username FROM Likers WHERE IG_ID=?", (row[1],))
                        l_un = self.c.fetchone()[0]
                        l_tmp = [l_un, row[0]]
                        l.append(l_tmp)
                    tpl_vars['most_likers'] = l

                # Most comments
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get posts with most comments" + IGGrabber.ENDC)

                self.c.execute("SELECT COUNT(*) AS Qty, IG_ID FROM Comments "
                               "WHERE Created BETWEEN ? AND ? GROUP BY IG_ID ORDER BY Qty DESC LIMIT 0,10",
                               (since_date, self.today))
                rows = self.c.fetchall()
                if rows is None:
                    tpl_vars['most_commentators'] = ""
                else:
                    l = list()
                    for row in rows:
                        self.c.execute("SELECT Username FROM Likers WHERE IG_ID=?", (row[1],))
                        res = self.c.fetchall()
                        if len(res) == 0:
                            if self.debug3:
                                print(IGGrabber.WARNING + "Can't find user in likers, search in followers..."
                                      + IGGrabber.ENDC)
                            self.c.execute("SELECT Username FROM Followers WHERE IG_ID=?", (row[1],))
                            res1 = self.c.fetchall()
                            if len(res1) == 0:
                                if self.debug3:
                                    print(IGGrabber.WARNING + "Can't find user in followers, search in MiscPeople..."
                                          + IGGrabber.ENDC)
                                self.c.execute("SELECT Username FROM MiscPeople WHERE IG_ID=?", (row[1],))
                                res2 = self.c.fetchall()
                                if len(res2) == 0:
                                    if self.debug3:
                                        print(IGGrabber.WARNING
                                              + "Can't find user in MiscPeople, search on instagram..."
                                              + IGGrabber.ENDC)
                                    # Still unknown -> let Instagram find him!
                                    payload = {'access_token': IGGrabber.ig_access_token}
                                    r = requests.get('https://api.instagram.com/v1/users/' + row[1], params=payload)
                                    data1 = r.json()
                                    self.ig_calls += 1  # We made a call!
                                    # Are we allowed?
                                    if data1['meta']['code'] == 200:
                                        l_un = data1['data']['username']
                                        l_full = data1['data']['full_name']
                                    else:
                                        if self.debug3:
                                            print(IGGrabber.WARNING +
                                                  "Instagram forbids us to learn more about this person :("
                                                  + IGGrabber.ENDC)
                                        l_un = "UNKNOWN"
                                        l_full = "UNKNOWN"

                                    # Add him to our database!
                                    self.c.execute("INSERT INTO MiscPeople (IG_ID, Username, FullName) VALUES (?,?,?)",
                                                   (row[1], l_un, l_full))
                                else:
                                    for r in res2:
                                        l_un = r[0]
                            else:
                                for r in res1:
                                    l_un = r[0]
                        else:
                            for r in res:
                                l_un = r[0]

                        l_tmp = [l_un, row[0]]
                        l.append(l_tmp)
                    tpl_vars['most_commentators'] = l

                # Most liked post
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get most liked post" + IGGrabber.ENDC)

                self.c.execute("SELECT Created, Link, Location, Likes, Comments, ImageURL, Descr FROM Media "
                               "WHERE Created BETWEEN ? AND ? ORDER BY Likes DESC LIMIT 0,1", (since_date, self.today))
                data = self.c.fetchone()
                # If there isn't a post show empty values!
                if data is None:
                    tpl_vars['most_liked_url'] = "#"
                    tpl_vars['most_liked_picurl'] = "nopic.jpg"
                    tpl_vars['most_liked_likes'] = "0"
                    tpl_vars['most_liked_comments'] = "0"
                    tpl_vars['most_liked_location'] = ""
                    tpl_vars['most_liked_descr'] = ""
                    tpl_vars['most_liked_date'] = "-"
                else:
                    tpl_vars['most_liked_url'] = data[1]
                    tpl_vars['most_liked_picurl'] = data[5]
                    tpl_vars['most_liked_likes'] = data[3]
                    tpl_vars['most_liked_comments'] = data[4]
                    tpl_vars['most_liked_location'] = data[2]
                    tpl_vars['most_liked_descr'] = data[6]
                    d = datetime.datetime.strptime(data[0], '%Y-%m-%d %H:%M:%S')
                    tpl_vars['most_liked_date'] = d.strftime("%d.%m.%Y %H:%M")

                # Most commented post
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get most commented post" + IGGrabber.ENDC)

                self.c.execute("SELECT Created, Link, Location, Likes, Comments, ImageURL, Descr FROM Media "
                               "WHERE Created BETWEEN ? AND ? ORDER BY Comments DESC LIMIT 0,1", (since_date, self.today))
                data = self.c.fetchone()
                # If there isn't a post show empty values!
                if data is None:
                    tpl_vars['most_commented_url'] = "#"
                    tpl_vars['most_commented_picurl'] = "nopic.jpg"
                    tpl_vars['most_commented_likes'] = "0"
                    tpl_vars['most_commented_comments'] = "0"
                    tpl_vars['most_commented_location'] = ""
                    tpl_vars['most_commented_descr'] = ""
                    tpl_vars['most_commented_date'] = "-"
                else:
                    tpl_vars['most_commented_url'] = data[1]
                    tpl_vars['most_commented_picurl'] = data[5]
                    tpl_vars['most_commented_likes'] = data[3]
                    tpl_vars['most_commented_comments'] = data[4]
                    tpl_vars['most_commented_location'] = data[2]
                    tpl_vars['most_commented_descr'] = data[6]
                    d = datetime.datetime.strptime(data[0], '%Y-%m-%d %H:%M:%S')
                    tpl_vars['most_commented_date'] = d.strftime("%d.%m.%Y %H:%M")

                # Most used tags
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get most used tags" + IGGrabber.ENDC)

                self.c.execute("SELECT Name, Qty FROM Tags "
                               "WHERE (LastUsed BETWEEN ? AND ?) AND (LastUsed IS NOT ?) ORDER BY Qty DESC LIMIT 0,10",
                               (since_date, self.today, firstrowdate))
                tpl_vars['most_tags'] = self.c.fetchall()

                # Most used filters
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get most used filters" + IGGrabber.ENDC)

                self.c.execute("SELECT Filter, COUNT(*) AS Qty FROM Media WHERE Created BETWEEN ? AND ? "
                               "GROUP BY Filter ORDER BY Qty DESC LIMIT 0,20", (since_date, self.today))
                tpl_vars['most_filters'] = self.c.fetchall()

                # Changed username
                if self.debug2:
                    print(IGGrabber.OKBLUE + "Get changed usernames" + IGGrabber.ENDC)

                self.c.execute("SELECT UsernameOld, UsernameNew FROM NameChanges WHERE Changed BETWEEN ? AND ? "
                               "ORDER BY UsernameNEW ASC", (since_date, self.today))
                tpl_vars['changedNames'] = self.c.fetchall()

                # Generate template
                if self.debug:
                    print(IGGrabber.OKBLUE + "Generating template from file" + IGGrabber.ENDC)

                tplenv = jinja2.Environment(loader=jinja2.FileSystemLoader(IGGrabber.tpl_path))
                # Load template
                tpl = tplenv.get_template(templatefile)
                # Create
                output = tpl.render(tpl_vars)
                # Save to file
                with codecs.open(IGGrabber.tpl_save_dir + "/" + templatefile, 
		encoding='utf-8', mode='w+') as file_:
                    file_.write(str(output))

            # ----------
            # Finished daily / weekly / monthly / yearly / overall stats
            # Let's process followers and media stats

            # -----
            # Follower stats
            if self.debug:
                print(IGGrabber.WARNING + "Creating follower stats" + IGGrabber.ENDC)

            templatefile = "follower.html"
            tpl_vars = dict()
            tpl_vars['title'] = "Follower - IG Stats - " + username
            tpl_vars['description'] = "Follower stats for Instagram account " + username
            tpl_vars['u_username'] = username
            tpl_vars['gentime'] = time.strftime("%d.%m.%Y %H:%M:%S")

            # We only want followers who were last seen on our last run. So get the latest LastSeen!
            self.c.execute("SELECT LastSeen FROM Followers ORDER BY LastSeen DESC LIMIT 0,1")
            lastseen = self.c.fetchone()[0]
            
            # Same for following
            self.c.execute("SELECT LastSeen FROM Following ORDER BY LastSeen DESC LIMIT 0,1")
            lastseenfollowing = self.c.fetchone()[0]

            # Follower (avg, min, max, overall)
            self.c.execute("SELECT MAX(Followers) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['follower_max'] = self.c.fetchone()[0]
            self.c.execute("SELECT MIN(Followers) FROM Followers WHERE Followers > 0 AND LastSeen=?", (lastseen,))
            tpl_vars['follower_min'] = self.c.fetchone()[0]
            self.c.execute("SELECT ROUND(AVG(Followers), 1) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['follower_avg'] = self.c.fetchone()[0]
            self.c.execute("SELECT SUM(Followers) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['follower_sum'] = self.c.fetchone()[0]

            # Following (avg, min, max, overall)
            self.c.execute("SELECT MAX(Following) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['following_max'] = self.c.fetchone()[0]
            self.c.execute("SELECT MIN(Following) FROM Followers WHERE Following > 0 AND LastSeen=?", (lastseen,))
            tpl_vars['following_min'] = self.c.fetchone()[0]
            self.c.execute("SELECT ROUND(AVG(Following), 1) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['following_avg'] = self.c.fetchone()[0]
            self.c.execute("SELECT SUM(Following) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['following_sum'] = self.c.fetchone()[0]

            # Media (avg, min, max)
            self.c.execute("SELECT MAX(Media) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['media_max'] = self.c.fetchone()[0]
            self.c.execute("SELECT MIN(Media) FROM Followers WHERE Media > 0 AND LastSeen=?", (lastseen,))
            tpl_vars['media_min'] = self.c.fetchone()[0]
            self.c.execute("SELECT ROUND(AVG(Media), 1) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['media_avg'] = self.c.fetchone()[0]
            self.c.execute("SELECT SUM(Media) FROM Followers WHERE LastSeen=?", (lastseen,))
            tpl_vars['media_sum'] = self.c.fetchone()[0]

            # Most follower
            self.c.execute("SELECT ProfilePicURL, Username, Followers "
                           "FROM Followers WHERE LastSeen=? ORDER BY Followers DESC LIMIT 0,10", (lastseen,))
            tpl_vars['most_follower'] = self.c.fetchall()

            # Most following
            self.c.execute("SELECT ProfilePicURL, Username, Following "
                           "FROM Followers WHERE LastSeen=? ORDER BY Following DESC LIMIT 0,10", (lastseen,))
            tpl_vars['most_following'] = self.c.fetchall()

            # Most media
            self.c.execute("SELECT ProfilePicURL, Username, Media "
                           "FROM Followers WHERE LastSeen=? ORDER BY Media DESC LIMIT 0,10", (lastseen,))
            tpl_vars['most_media'] = self.c.fetchall()

            # Following each other (you <-> your follower)
            eachother = 0
            self.c.execute("SELECT IG_ID FROM Followers WHERE LastSeen=?", (lastseen,))
            follower_ids_raw = self.c.fetchall()
            follower_ids = list()
            for a in follower_ids_raw:
                follower_ids.append(a[0])

            self.c.execute("SELECT IG_ID FROM Following WHERE LastSeen=?", (lastseenfollowing,))
            rows = self.c.fetchall()
            for row in rows:
                # Iterate through follower and look if it's in there
                if row[0] in follower_ids:
                    eachother += 1
            tpl_vars['follow_each_other'] = eachother

            # Following you but you don't follow them
            follow_you = 0
            follow_you_list = list()
            # Following them (create nice list)
            self.c.execute("SELECT IG_ID FROM Following WHERE LastSeen=?", (lastseenfollowing,))
            following_ids_raw = self.c.fetchall()
            following_ids = list()
            for a in following_ids_raw:
                following_ids.append(a[0])

            # Following me
            self.c.execute("SELECT IG_ID FROM Followers WHERE LastSeen=? ORDER BY Followers DESC", (lastseen,))
            rows = self.c.fetchall()
            for row in rows:
                # Person is following me
                # Check if I'm not following -> then make suggestion!
                if row[0] not in following_ids:
                    # Add person to suggestion list (only 20!)
                    if follow_you < 20:
                        self.c.execute("SELECT Username, ProfilePicURL FROM Followers WHERE IG_ID=?", (row[0],))
                        t = self.c.fetchall()
                        for s in t:
                            unm = s[0]
                            url = s[1]
                        follow_you_list.append([url, unm])

                    # Increase counter
                    follow_you += 1
            tpl_vars['follow_you_only'] = follow_you
            tpl_vars['follow_you_list'] = follow_you_list

            # You follow them but they don't follow you
            follow_them = 0
            self.c.execute("SELECT IG_ID FROM Following WHERE LastSeen=?", (lastseenfollowing,))
            rows = self.c.fetchall()
            for row in rows:
                # if follower not in your follower list!
                if row[0] not in follower_ids:
                    follow_them += 1
            tpl_vars['follow_them_only'] = follow_them

            # People who like your media but you don't follow them (sort by likes) (20 people)
            # People you follow: following_ids, People who like my media: Likers
            like_not_follow = list()
            self.c.execute("SELECT Liker, COUNT(Media) AS cnt FROM Likers_Media "
                           "GROUP BY Liker ORDER BY cnt DESC LIMIT 0,20")
            rows = self.c.fetchall()
            for row in rows:
                # If person not in following list we can continue
                if row[0] not in following_ids:
                    # Get username
                    self.c.execute("SELECT Username FROM Likers WHERE IG_ID=?", (row[0],))
                    un = self.c.fetchone()[0]
                    # Add to return list (ID, username, count)!
                    like_not_follow.append([row[0], un, row[1]])
            tpl_vars['like_not_following'] = like_not_follow

            # People you follow but who don't like much from your media (20 people)
            follow_not_liking = list()
            # Create a nice list of likers
            self.c.execute("SELECT IG_ID FROM Likers")
            likers_raw = self.c.fetchall()
            likers = list()
            for a in likers_raw:
                likers.append(a[0])

            # Iterate through followings
            for row in following_ids:
                if row not in likers and len(follow_not_liking) < 20:
                    # User didn't like anything :(
                    self.c.execute("SELECT Username, ProfilePicURL FROM Following WHERE IG_ID=?", (row,))
                    ppl = self.c.fetchone()
                    # Add to list (ID, username, profilepic)
                    follow_not_liking.append([row, ppl[0], ppl[1]])
            tpl_vars['following_not_liking'] = follow_not_liking

            # Not following anymore
            not_following_anymore = list()

            self.c.execute("SELECT IG_ID, Username, ProfilePicURL, LastSeen FROM Followers "
                           "WHERE LastSeen<? ORDER BY LastSeen DESC LIMIT 0,20", (lastseen,))
            rows = self.c.fetchall()
            for row in rows:
                lastseendate = time.strptime(row[3], "%Y-%m-%d")
                lastseendate1 = time.strftime("%d.%m.", lastseendate)
                not_following_anymore.append([row[1], row[2], lastseendate1, row[0]])

            tpl_vars['not_following_anymore'] = not_following_anymore

            self.c.execute("SELECT IG_ID FROM Followers WHERE LastSeen<?", (lastseen,))
            not_following_anymore_count = self.c.fetchall()
            tpl_vars['not_following_anymore_count'] = len(not_following_anymore_count)

            # ---
            # Generate template
            if self.debug:
                print(IGGrabber.OKBLUE + "Generating template from file" + IGGrabber.ENDC)

            tplenv = jinja2.Environment(loader=jinja2.FileSystemLoader(IGGrabber.tpl_path))
            # Load template
            tpl = tplenv.get_template(templatefile)
            # Create
            output = tpl.render(tpl_vars)
            # Save to file
            with open(IGGrabber.tpl_save_dir + "/" + templatefile, 'w') as file_:
                file_.write(str(output))

            # -----
            # Media stats
            if self.debug:
                print(IGGrabber.WARNING + "Creating media stats" + IGGrabber.ENDC)

            templatefile = "media.html"
            tpl_vars = dict()
            tpl_vars['title'] = "Media - IG Stats - " + username
            tpl_vars['description'] = "Media stats for Instagram account " + username
            tpl_vars['u_username'] = username
            tpl_vars['gentime'] = time.strftime("%d.%m.%Y %H:%M:%S")

            # Top 8 liked pics
            self.c.execute("SELECT Created, Link, Location, Likes, Comments, ImageURL, Descr "
                           "FROM Media ORDER BY Likes DESC LIMIT 0,8")
            tpl_vars['most_liked'] = self.c.fetchall()

            # Top 8 commented pics
            self.c.execute("SELECT Created, Link, Location, Likes, Comments, ImageURL, Descr "
                           "FROM Media ORDER BY Comments DESC LIMIT 0,8")
            tpl_vars['most_commented'] = self.c.fetchall()

            # Big tag-list
            self.c.execute("SELECT Name, Qty, LastUsed FROM Tags ORDER BY Qty DESC LIMIT 0,39")
            tpl_vars['tags'] = self.c.fetchall()

            # Most comments
            # by time
            self.c.execute("SELECT strftime('%H', Created) as Hour, Count(*) FROM Comments GROUP BY Hour")
            # [0] -> Hour, [1] -> Count
            tpl_vars['comments_sum_hour'] = self.c.fetchall()
            # by day
            self.c.execute("SELECT strftime('%w', Created) as Day, Count(*) FROM Comments GROUP BY Day")
            # [0] -> Day of week (0-6, 0 -> sunday), [1] -> Count
            formatted_list = list()
            rows = self.c.fetchall()
            for row in rows:
                if row[0] == "0":
                    formatted_list.append(["Sun", row[1]])
                elif row[0] == "1":
                    formatted_list.append(["Mon", row[1]])
                elif row[0] == "2":
                    formatted_list.append(["Tue", row[1]])
                elif row[0] == "3":
                    formatted_list.append(["Wed", row[1]])
                elif row[0] == "4":
                    formatted_list.append(["Thu", row[1]])
                elif row[0] == "5":
                    formatted_list.append(["Fri", row[1]])
                elif row[0] == "6":
                    formatted_list.append(["Sat", row[1]])

            tpl_vars['comments_sum_day'] = formatted_list

            # Most likes by weekday
            # Ignore likes from first day because there was init, so all likes yet are on this day!
            self.c.execute("SELECT History FROM User ORDER BY History ASC LIMIT 0,1")
            firstrowdate = self.c.fetchone()[0]
            self.c.execute("SELECT strftime('%w', Created) as Day, Count(*) FROM Likers_Media "
                           "WHERE Created IS NOT ? GROUP BY Day", (firstrowdate,))
            # [0] -> Day of week (0-6, 0 -> sunday), [1] -> Count
            formatted_list = list()
            rows = self.c.fetchall()
            for row in rows:
                if row[0] == "0":
                    formatted_list.append(["Sun", row[1]])
                elif row[0] == "1":
                    formatted_list.append(["Mon", row[1]])
                elif row[0] == "2":
                    formatted_list.append(["Tue", row[1]])
                elif row[0] == "3":
                    formatted_list.append(["Wed", row[1]])
                elif row[0] == "4":
                    formatted_list.append(["Thu", row[1]])
                elif row[0] == "5":
                    formatted_list.append(["Fri", row[1]])
                elif row[0] == "6":
                    formatted_list.append(["Sat", row[1]])

            tpl_vars['likes_sum_day'] = formatted_list

            # Most posts
            # by time
            self.c.execute("SELECT strftime('%H', Created) as Hour, Count(*) FROM Media GROUP BY Hour")
            # [0] -> Hour, [1] -> Count
            tpl_vars['posts_sum_hour'] = self.c.fetchall()
            # by day
            self.c.execute("SELECT strftime('%w', Created) as Day, Count(*) FROM Media GROUP BY Day")
            # [0] -> Day of week (0-6, 0 -> sunday), [1] -> Count
            formatted_list = list()
            rows = self.c.fetchall()
            for row in rows:
                if row[0] == "0":
                    formatted_list.append(["Sun", row[1]])
                elif row[0] == "1":
                    formatted_list.append(["Mon", row[1]])
                elif row[0] == "2":
                    formatted_list.append(["Tue", row[1]])
                elif row[0] == "3":
                    formatted_list.append(["Wed", row[1]])
                elif row[0] == "4":
                    formatted_list.append(["Thu", row[1]])
                elif row[0] == "5":
                    formatted_list.append(["Fri", row[1]])
                elif row[0] == "6":
                    formatted_list.append(["Sat", row[1]])

            tpl_vars['posts_sum_day'] = formatted_list

            # ---
            # Generate template
            if self.debug:
                print(IGGrabber.OKBLUE + "Generating template from file" + IGGrabber.ENDC)

            tplenv = jinja2.Environment(loader=jinja2.FileSystemLoader(IGGrabber.tpl_path))
            # Load template
            tpl = tplenv.get_template(templatefile)
            # Create
            output = tpl.render(tpl_vars)
            # Save to file
            with open(IGGrabber.tpl_save_dir + "/" + templatefile, 'w') as file_:
                file_.write(str(output))

        # --------------------
        # Exception Handling
        except KeyboardInterrupt:
            print(IGGrabber.WARNING + "Exiting IG Grabber." + IGGrabber.ENDC)

        except Exception:
            traceback.print_exc(file=sys.stdout)

        # --- END HTMLSTATS  # --------------------

    def outputstats(self):
        # ----------
        # Stats
        if self.debug:
            print(IGGrabber.HEADER + "")
            print("+------------------------------------------------------------")
            # Output API calls if possible
            try:
                ig_calls = self.ig_calls
                print("| Total API calls: " + str(ig_calls))
            except AttributeError:
                pass

            # Output follower stats if possible
            try:
                f = self.follower
                f_new = self.f_newfollower
                print("| Your stats: " + str(f) + " followers (" + str(f_new) + " new)")
            except AttributeError:
                pass

            try:
                f2 = self.follows
                fw = self.f_newfollowing
                print("| Your stats: " + str(f2) + " following ( " + str(fw) + " new)")
            except AttributeError:
                pass

            # Output media stats if possible
            try:
                m_c = self.m_count
                m_l = self.m_new_likes
                m_n = self.m_new_comments
                print("| Media: " + str(m_c) + " (" + str(m_l) + " new like(s), " + str(m_n) + " new comment(s))")
            except AttributeError:
                pass
            # Bottom line
            print("+------------------------------------------------------------" + IGGrabber.ENDC)

# Running
if __name__ == '__main__':
    # Init
    sw = IGGrabber()

    # Accepting arguments
    if len(sys.argv) == 2:
        # Only one accepted!
        # First argument is script name (getIGstat.py)
        argument = str(sys.argv[1])

        # Update follower informations
        if argument == "follower":
            # Do a full update!
            sw.updatefollowerdata(True)
            sw.outputstats()
        # Update following informations
        elif argument == "follows":
            sw.updatefollowingdata()
            sw.outputstats()
        # Update media informations
        elif argument == "media":
            sw.updatemediadata()
            sw.outputstats()
        # Create stats
        elif argument == "stats":
            sw.htmlstats()
        # Show help
        elif argument == "help":
            print("IG Grabber " + IGGrabber.version)
            print("Usage: ./getIGstat.py {follower|follows|media|stats|help} ")
            print("Or leave empty for all.")
        else:
            sw.main()

    else:
        # No arguments -> main method
        sw.main()
