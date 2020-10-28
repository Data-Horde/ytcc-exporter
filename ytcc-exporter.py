from datetime import timedelta

from json import dumps, loads

from gc import collect

import requests

from time import sleep

import re

# https://docs.python.org/3/library/html.parser.html
from html.parser import HTMLParser
# Beautiful Soup
from bs4 import BeautifulSoup

# This function adapted from https://github.com/cdown/srt/blob/11089f1e021f2e074d04c33fc7ffc4b7b52e7045/srt.py, lines 69 and 189 (MIT License)
def timedelta_to_sbv_timestamp(timedelta_timestamp):
    r"""
    Convert a :py:class:`~datetime.timedelta` to an SRT timestamp.
    .. doctest::
        >>> import datetime
        >>> delta = datetime.timedelta(hours=1, minutes=23, seconds=4)
        >>> timedelta_to_sbv_timestamp(delta)
        '01:23:04,000'
    :param datetime.timedelta timedelta_timestamp: A datetime to convert to an
                                                   SBV timestamp
    :returns: The timestamp in SBV format
    :rtype: str
    """

    SECONDS_IN_HOUR = 3600
    SECONDS_IN_MINUTE = 60
    HOURS_IN_DAY = 24
    MICROSECONDS_IN_MILLISECOND = 1000

    hrs, secs_remainder = divmod(timedelta_timestamp.seconds, SECONDS_IN_HOUR)
    hrs += timedelta_timestamp.days * HOURS_IN_DAY
    mins, secs = divmod(secs_remainder, SECONDS_IN_MINUTE)
    msecs = timedelta_timestamp.microseconds // MICROSECONDS_IN_MILLISECOND
    return "%1d:%02d:%02d.%03d" % (hrs, mins, secs, msecs)

# Utility functions from backYouTubePyCollection (https://github.com/Data-Horde/backUpYouTubePyCollection)

def isChannelURL(s):
    return (s.find("www.youtube.com/channel") != -1)

def isUserURL(s):
    return (s.find("www.youtube.com/user") != -1) or (s.find("www.youtube.com/c/") != -1)

def getUserFromChannel(s):
    splitUp=s.split('/')
    return splitUp[splitUp.index('channel')+1]

def getUserFromUrl(s):
    splitUp=s.split('/')
    if 'user' in splitUp:
        return splitUp[splitUp.index('user')+1]
    return splitUp[splitUp.index('c')+1]

def getList(s):
    try:
        return re.findall(r'list=[^&#]+',s)[0][5:]
    except:
        return None

#Unused
def channelIDInvalid(id):
    if id.find('youtube.com') != -1 or id.find('youtu.be') != -1:
        return True
    r=requests.get("https://www.youtube.com/channel/{}".format(id))
    if r.status_code != 200 and r.status_code != 404:
        return False
    if r.text.find("empty-channel-banner") != -1:
        return True
    return False
#Unused END

#Analyze Playlist
def analyzePlaylist(pID):

    p=[]

    try:
        #First link is extracted as an html
        target="https://www.youtube.com/playlist?list={}".format(pID)
        while True:
            r=requests.get(target)

            if r.status_code != 200:
                #t.cancel()
                print("An error occured while trying to read the playlist...")
                action=""
                while action!='r' and action!='a'  :
                    action = input("Type r to retry or a to abort:\n")
                    action = action.rstrip().strip()
                if action == 'r':
                    #reportProgress()
                    continue
                if action == 'a':
                    return p,1 
            break
        plt=r.text
        imAtSoup = BeautifulSoup(plt,"html.parser")


        #Layout HAS CHANGED SINCE 2019, FIXING!

        # Page no longer starts with first few items visible,

        # Hacking into JSON object where first 100 playlist videos are stashed
        scripts = [ script.contents[0] for script in imAtSoup.find_all('script') if len(script.contents) > 0 and script.contents[0].find("responseContext")!=-1 ]
        JS = scripts[0]

        #Find the JSONOBJECT PASSED AFTER "window["ytInitialData"] = JSONOBJECT"
        JSON_START = JS.find("""window["ytInitialData"]""")+26
        JSON_END = JS.find("""window["ytInitialPlayerResponse"]""")-37
        JASON=JS[JSON_START:JSON_START+JSON_END]

        #Parse the JSON to collect links
        #with open("f.json","w") as f:
        #    f.write(JASON)
        
        JSON = loads(JASON)

        BATCH=JSON["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"][0]["playlistVideoListRenderer"]["contents"]
        URLs = ["https://www.youtube.com/watch?v={}".format(x["playlistVideoRenderer"]["videoId"]) for x in BATCH]
        
        p.extend(URLs)
        #print(p)
        #print(SELECTION)
        #print("LEN: "+str(len(SELECTION)))

        #print("P")
        #print(p)

        nB = imAtSoup.find_all("button", class_="load-more-button")
        if len(nB) == 0:
            return p,0
        ajaxTarget=nB[0].get("data-uix-load-more-href")
        target = "https://www.youtube.com{}".format(ajaxTarget)
        while True:
            #later playlist links are the internal html of a json
            #and to be loaded links are stored in a seperate entry of said json 
            #print(target)
            #print(plt.find('browse_ajax?ctoken='))
            Break=False
            while True:
                #print(target)
                r=requests.get(target)
                #print(r.status_code)
                if r.status_code != 200:
                    t.cancel()
                    print("An error occured while trying to read the upload playlist...")
                    action=""
                    while action!='r' and action!='a':
                        action = input("Type r to retry or a to abort:\n")
                        action = action.rstrip().strip()
                    if action == 'r':
                        reportPlaylistProgress()
                        continue
                    if action == 'a':
                        return p,1
                break
            plt=r.json()['content_html']
            imAtSoup = BeautifulSoup(plt,"html.parser")
            for link in imAtSoup.find_all("a", class_="pl-video-title-link"):
                p.append(idExtractor('https://www.youtube.com{}'.format(link.get('href'))))
            nextLink=r.json()['load_more_widget_html']
            whereIsSoup = BeautifulSoup(nextLink,"html.parser")
            #print(whereIsSoup.prettify())
            nB = whereIsSoup.find_all("button", class_="load-more-button")
            if len(nB) == 0:
                return p,0
            ajaxTarget=nB[0].get("data-uix-load-more-href")
            target = "https://www.youtube.com{}".format(ajaxTarget)
            #return 0
            #print(plt)
            #return 1
    except Exception as e:
        print(e)
        return [],1
    else:
        return p,0

#Get user playlist for "rare" channel URLs
def getuPLink(customURL,tid):
    userPage=""
    aborted=False
    while True:
        r = None

        if customURL:
            r = requests.get("https://www.youtube.com/c/{}/videos".format(tid))
        else:
            r = requests.get("https://www.youtube.com/user/{}/videos".format(tid))

        if r.status_code != 200:
            print("An error occured while trying to load the channel...")
            print(r.status_code)
            action=""
            while action!='r' and action!='a'  :
                action = input("Type r to retry or a to abort:\n")
                action = action.rstrip().strip()
            if action == 'r':
                continue
            elif action == 'a':
                break

        userPage = r.text
        break
    
    if aborted:
        return ("", False)

    lazySearch = userPage.find('/channel/UC')
    uP=userPage[lazySearch+9:userPage.find('"',lazySearch+10)]
    #print("uP")
    #print(uP)
    uPLink = "https://www.youtube.com/playlist?list={}".format("UU"+uP[2:])
    return (uPLink, True)

#DUMP USER PLAYLIST
def dumpuPL(uPLink):
    #uPLink = "https://www.youtube.com{}".format(uP.get('href'))
            
    lID = getList(uPLink)

    #print(lID)
    print("getting upload playlist for {}".format(lID))

    #Go to the playlist page using teh id
    #might not have time to add this
    #reportPlaylistProgress()
    p, err = analyzePlaylist(lID)
    
    if err==1:
        return
    else:
        print("Public Video Count for this Channel: {}".format(len(p)))

    # print("First Upload Date: {}".format(getVideoDate(p[len(p)-1])))
    # print("Latest Upload Date: {}".format(getVideoDate(p[0])))

    # print("****************************************************")
    
    # print("Optionally you may specify the interval of the videos to be scanned")
    # print("as two dates in YYYY-MM-DD format on a single line.")
    # print("Otherwise hit enter")
    # print("By default the start date will be set to 2005-04-23")
    # print("And the end date to 2017-05-03 (the day after annotation editing was removed)")
    # #Query date
    # #print(getVideoDate(p[0]))
    # #Format is year-month-day
    # #4-2-2

    # #index=dateSearch(dateConvert("2017-05-10"),p,0,len(p)-1,False)
    # sdate=datetime(2005,4,23)
    # edate=datetime(2017,5,3)
    # #sdate=datetime(getVideoDate(p[len(p)-1])

    # while True:
    #     inp = input()
    #     inp = inp.strip().rstrip()
        
    #     if inp=="":
    #         break

    #     elif not isTwoDates(inp):
    #         print("Unrecognized input")
    #         continue
    #     try:
    #         sC,eC = getTwoDates(inp)
    #         #print (sC,eC)
    #         d1 = dateConvert(sC)
    #         d2 = dateConvert(eC)
    #         #print (d1,d2)
    #         if not validTwoDates(d1,d2):
    #             print("Invalid interval, make sure you wrote the start date first!")
    #             continue
    #         print("Adjusting Interval...")
    #         sdate = max(d1,sdate)
    #         edate = min(d2,edate)
    #         break
    #     except:
    #         print("Unable to convert input to date format")
    #         continue

    # #y,m,d = map( int, sC.split('-') )
    
    # #y,m,d = map( int, sC.split('-') )
    
    # #indexS = 0
    # #if sdate != getVideoDate(p[0]):
    # indexS=dateSearch(edate,p,0,len(p)-1,False)

    # #Special Case:
    # #If date is 4 23 2005 it's len(p)-1
    # indexE=len(p)-1
    # if edate != datetime(2005,4,23):
    #     indexE=dateSearch(sdate,p,0,len(p)-1,True)

    # #print(indexS,indexE)
    # #print("error handle index later:")

    # #print(index)
    # #return
    # #sdate = 0
    # #edate = len(p)+1

    # """
    # while True:
    #     print("Type the index of the video you want to start from and the index of the last one you'd like to include.")
    #     print("Or simply press enter without typing anything to scan the full playlist...")
    #     intervalInput = input()
    #     if contains2Numbers(intervalInput):
    #         start,end = get2Numbers(intervalInput)
    #         if validInterval(start,end,len(p)):
    #             end+=1
    #             break
    #         else:
    #             print("Please specify a valid interval!")
    #     elif intervalInput=="":
    #         start = 0
    #         end = len(p)+1
    #         break
    #     else:
    #         print("Please type only two numbers representing indices in the playlist if you wish to specify an interval OR press enter to skip.")
    # #In the case of a playlist sweep ALSO take a snapshot of the playlist
    
    # if start == 0 and end == len(p)+1:
    #     playListSweep = True
    # """
    # playListSweep = False
    # if indexS == 0 and indexE == len(p)-1:
    #     playListSweep = True
    # p = p[indexS:indexE+1]

    # #print(indexS,indexE)
    # #print(p)

    # #Adjust hard limit so it goes beyond the playlist
    # hardLimitSet = False 
    # #err = setHardLimit()
    # #if err ==1:
    # #continue
    # setHardLimit()

    # channelLock = False 
    # err = setChannelLock()
    # if err ==1:
    #     continue

    # mode1 = False 
    # setMode()


    # #vID = idExtractor(argument)
    # #print("vID: {}".format(vID))
    # #r = annotationsBackedUp(vID)
    # #if 'closest' in r.json()["archived_snapshots"]:
    # #   print('That link seems to have been saved.')
    # #   isY = input('But if you want to make sure that all sublinks have also been saved type y\n')
    # #   if isY.rstrip().strip() != "y":
    # #       continue

    # #gather videos linked to from this playlist
    # #print (p)
    # #continue

    # Break = False
    # while True:
    #     err = activateChannelLock(idExtractor(p[0]))
    #     if err == 1:
    #         print("an error occured while trying to access the channel")
    #         action=""
    #         while action!='r' and action!='a':
    #             action = input("Type r to retry or a to abort:\n")
    #             action = action.rstrip().strip()
    #         if action == 'r':
    #             continue
    #         if action == 'a':
    #             Break = True
    #             break
    #     break
    # if Break:
    #     continue

    # err = gatherStartingFromPlaylistVids()
    # t.cancel()
    # if err == 1:
    #     Break=True
    #     continue

    # #mode 2
    #     toGather = len(m)
    #     print("Discovered {} videos...".format(toGather))

    #     i=0
    #     successes=0
    #     Break=False
    #     reportProgress()
    #     #t.start()
    #     for ID in m:
    #         while True:
    #             code = backUp(ID)
    #             if code == 1:
    #                 t.cancel()
    #                 # #19 is problematic
    #                 print("https://www.youtube.com/watch?v={} wasn't saved properly".format(ID))
    #                 action=""
    #                 while action!='r' and action!='a' and action!='i':
    #                     action = input("Type r to retry,i to ignore or a to abort:\n")
    #                     action = action.rstrip().strip()
    #                 if action == 'r':
    #                     reportProgress()
    #                     continue
    #                 if action == 'i':
    #                     reportProgress()
    #                     i+=1
    #                     break
    #                 if action == 'a':
    #                     Break=True
    #                     playListSweep = False
    #                     i+=1
    #                     break
    #             elif code == 2:
    #                 print("https://www.youtube.com/watch?v={} is unavailable, skipping...".format(ID))
    #                 i+=1
    #                 break
    #             else:
    #                 m[ID]=True
    #                 i+=1
    #                 successes+=1
    #                 break
    #         if Break:
    #             break
    #     t.cancel()
    #     if toGather == 1:
    #         print("{}/{} is now backed up!".format(successes,toGather))
    #     print("{}/{} are now backed up!".format(successes,toGather))
    
    # #mode 1
    # else:
    #     print("DONE!")
    #     print("{}/{} backed up!".format(successes,len(m)))


    # if playListSweep:
    #     snapShotOfPlaylist(lID)
    #     print("Took a snapshot of the playlist to let people know its been fully scanned.")
# Utilities End Here!

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.captions = []
        self.title = ""
        self.description = ""
        self.inittitle = ""
        self.initdescription = ""


    def check_attr(self, attrs, attr, value):
        for item in attrs:
            if item[0] == attr and item[1] == value:
                return True
        return False

    def get_attr(self, attrs, attr):
        for item in attrs:
            if item[0] == attr:
                return item[1]
        return False

    def handle_starttag(self, tag, attrs):
        if tag == "input" and self.check_attr(attrs, "class", "yt-uix-form-input-text event-time-field event-start-time"):
            self.captions.append({"startTime": int(self.get_attr(attrs, "data-start-ms")), "text": ""})
        elif tag == "input" and self.check_attr(attrs, "class", "yt-uix-form-input-text event-time-field event-end-time"):
            self.captions[len(self.captions)-1]["endTime"] = int(self.get_attr(attrs, "data-end-ms"))
        elif tag == "input" and self.check_attr(attrs, "id", "metadata-title"):
            self.title = self.get_attr(attrs, "value")
        elif tag == "textarea" and self.check_attr(attrs, "id", "metadata-description"):
            self.initdescription = self.get_attr(attrs, "data-original-description")

    def handle_data(self, data):
        if self.get_starttag_text() and self.get_starttag_text().startswith("<textarea "):
            if 'name="serve_text"' in self.get_starttag_text():
                self.captions[len(self.captions)-1]["text"] += data
            elif 'id="metadata-description"' in self.get_starttag_text():
                self.description += data
        elif self.get_starttag_text() and self.get_starttag_text().startswith('<div id="original-video-title"'):
            self.inittitle += data

def subprrun(jobs, mysession):
    while not jobs.empty():
        collect() #cleanup memory
        langcode, vid, mode = jobs.get()
        vid = vid.strip()
        print(langcode, vid)

        while True:
            if mode == "default":
                pparams = (
                    ("v", vid),
                    ("lang", langcode),
                    ("action_mde_edit_form", 1),
                    ("bl", "vmp"),
                    ("ui", "hd"),
                    ("tab", "captions"),
                    ("o", "U")
                )

                page = mysession.get("https://www.youtube.com/timedtext_editor", params=pparams)
            elif mode == "forceedit-metadata":
                pparams = (
                    ("v", vid),
                    ("lang", langcode),
                    ("action_mde_edit_form", 1),
                    ('forceedit', 'metadata'),
                    ('tab', 'metadata')
                )

                page = mysession.get("https://www.youtube.com/timedtext_editor", params=pparams)
            elif mode == "forceedit-captions":
                pparams = (
                    ("v", vid),
                    ("lang", langcode),
                    ("action_mde_edit_form", 1),
                    ("bl", "vmp"),
                    ("ui", "hd"),
                    ('forceedit', 'captions'),
                    ("tab", "captions"),
                    ("o", "U")
                )

                page = mysession.get("https://www.youtube.com/timedtext_editor", params=pparams)

            if not "accounts.google.com" in page.url:
                break
            else:
                print("[Retrying in 30 seconds] Please supply authentication cookie information in config.json or environment variables. See README.md for more information.")
                sleep(30)

        inttext = page.text

        try:
            initlang = page.text.split("'metadataLanguage': \"", 1)[1].split('"', 1)[0]
        except:
            initlang = ""

        del page

        filestring = "_community_draft"
        
        if '<li id="captions-editor-nav-captions" role="tab" data-state="published" class="published">' in inttext:
            filestring = "_community_published"

        if mode == "forceedit-captions":
            filestring = "_community_draft"

        if 'title="The video owner already provided subtitles/CC"' in inttext:
            filestring = "_uploader_provided"

        if not "forceedit" in mode:
            if '&amp;forceedit=metadata&amp;tab=metadata">See latest</a>' in inttext:
                jobs.put((langcode, vid, "forceedit-metadata"))

            if '<li id="captions-editor-nav-captions" role="tab" data-state="published" class="published">' in inttext:
                jobs.put((langcode, vid, "forceedit-captions"))

        if 'id="reject-captions-button"' in inttext or 'id="reject-metadata-button"' in inttext or 'data-state="published"' in inttext or 'title="The video owner already provided subtitles/CC"' in inttext: #quick way of checking if this page is worth parsing
            parser = MyHTMLParser()
            parser.feed(inttext)

            captiontext = False
            for item in parser.captions:
                if item["text"][:-9]:
                    captiontext = True

            if captiontext and (mode == "default" or mode == "forceedit-captions"):
                myfs = open("out/"+vid+"/"+vid+"_"+langcode+filestring+".sbv", "w", encoding="utf-8")
                captions = parser.captions
                captions.pop(0) #get rid of the fake one
                while captions:
                    item = captions.pop(0)

                    myfs.write(timedelta_to_sbv_timestamp(timedelta(milliseconds=item["startTime"])) + "," + timedelta_to_sbv_timestamp(timedelta(milliseconds=item["endTime"])) + "\n" + item["text"][:-9] + "\n")
                    
                    del item
                    if captions:
                        myfs.write("\n")
                del captions
                myfs.close()
                del myfs

            del captiontext

            if (parser.title or parser.description[:-16]) and (mode == "default" or mode == "forceedit-metadata"):
                metadata = {}
                metadata["title"] = parser.title
                if metadata["title"] == False:
                    metadata["title"] = ""
                metadata["description"] = parser.description[:-16]

                filestring = "_community_draft"
                if '<li id="captions-editor-nav-metadata" role="tab" data-state="published" class="published">' in inttext:
                    filestring = "_community_published"

                if mode == "forceedit-metadata":
                    filestring = "_community_draft"
                open("out/"+vid+"/"+vid+"_"+langcode+filestring+".json", "w", encoding="utf-8").write(dumps(metadata))
                del metadata

            if (parser.inittitle[9:-17] or parser.initdescription) and (mode == "default" or mode == "forceedit-metadata" and initlang):
                metadata = {}
                metadata["title"] = parser.inittitle[9:-17]
                if metadata["title"] == False:
                    metadata["title"] = ""
                metadata["description"] = parser.initdescription

                filestring = "_uploader_provided"
                open("out/"+vid+"/"+vid+"_"+initlang+filestring+".json", "w", encoding="utf-8").write(dumps(metadata))
                del metadata

        del inttext

        del langcode
        del vid
        del pparams

        jobs.task_done()

    return True

if __name__ == "__main__":
    from os import environ, mkdir
    from os.path import isfile
    from json import loads
    #HSID, SSID, SID cookies required
    if "HSID" in environ.keys() and "SSID" in environ.keys() and "SID" in environ.keys():
        cookies = {"HSID": environ["HSID"], "SSID": environ["SSID"], "SID": environ["SID"]}
    elif isfile("config.json"):
        cookies = loads(open("config.json").read())
    else:
        print("HSID, SSID, and SID cookies from youtube.com are required. Specify in config.json or as environment variables.")
        assert False
    if not (cookies["HSID"] and cookies["SSID"] and cookies["SID"]):
        print("HSID, SSID, and SID cookies from youtube.com are required. Specify in config.json or as environment variables.")
        assert False

    mysession = requests.session()
    mysession.headers.update({"cookie": "HSID="+cookies["HSID"]+"; SSID="+cookies["SSID"]+"; SID="+cookies["SID"], "Accept-Language": "en-US",})
    del cookies
    from sys import argv
    from queue import Queue
    from threading import Thread
    langs = ['ab', 'aa', 'af', 'sq', 'ase', 'am', 'ar', 'arc', 'hy', 'as', 'ay', 'az', 'bn', 'ba', 'eu', 'be', 'bh', 'bi', 'bs', 'br', 
    'bg', 'yue', 'yue-HK', 'ca', 'chr', 'zh-CN', 'zh-HK', 'zh-Hans', 'zh-SG', 'zh-TW', 'zh-Hant', 'cho', 'co', 'hr', 'cs', 'da', 'nl', 
    'nl-BE', 'nl-NL', 'dz', 'en', 'en-CA', 'en-IN', 'en-IE', 'en-GB', 'en-US', 'eo', 'et', 'fo', 'fj', 'fil', 'fi', 'fr', 'fr-BE', 
    'fr-CA', 'fr-FR', 'fr-CH', 'ff', 'gl', 'ka', 'de', 'de-AT', 'de-DE', 'de-CH', 'el', 'kl', 'gn', 'gu', 'ht', 'hak', 'hak-TW', 'ha', 
    'iw', 'hi', 'hi-Latn', 'ho', 'hu', 'is', 'ig', 'id', 'ia', 'ie', 'iu', 'ik', 'ga', 'it', 'ja', 'jv', 'kn', 'ks', 'kk', 'km', 'rw', 
    'tlh', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'ln', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mni', 'mi', 'mr', 'mas', 'nan', 
    'nan-TW', 'lus', 'mo', 'mn', 'my', 'na', 'nv', 'ne', 'no', 'oc', 'or', 'om', 'ps', 'fa', 'fa-AF', 'fa-IR', 'pl', 'pt', 'pt-BR', 
    'pt-PT', 'pa', 'qu', 'ro', 'rm', 'rn', 'ru', 'ru-Latn', 'sm', 'sg', 'sa', 'sc', 'gd', 'sr', 'sr-Cyrl', 'sr-Latn', 'sh', 'sdp', 'sn', 
    'scn', 'sd', 'si', 'sk', 'sl', 'so', 'st', 'es', 'es-419', 'es-MX', 'es-ES', 'es-US', 'su', 'sw', 'ss', 'sv', 'tl', 'tg', 'ta', 
    'tt', 'te', 'th', 'bo', 'ti', 'tpi', 'to', 'ts', 'tn', 'tr', 'tk', 'tw', 'uk', 'ur', 'uz', 'vi', 'vo', 'vor', 'cy', 'fy', 'wo', 
    'xh', 'yi', 'yo', 'zu']
    vidl = argv
    vidl.pop(0)

    try:
        mkdir("out")
    except:
        pass

    jobs = Queue()
    for URL in vidl:

        #CHANNEL URL (we can derive the channel playlist from this with ease)
        if isChannelURL(URL):

            channel = URL

            #IF CHANNEL ID INVALID CONTINUE
            #if channelIDInvalid(getUserFromChannel(channel)):
            #    continue

            # TOO SLOW, GOING TO HAVE TO TRY/EXCEPT INTO PASS TO SEE SOME DECENT SPEED ON THIS ONE

            #print("GOT CHANNEL REQUEST: {}".format(channel))
            tid = getUserFromChannel(channel)
            uPLink = "https://www.youtube.com/playlist?list={}".format("UU"+tid[2:])
            print("COMMENT THIS OUT LATER A")
            print(uPLink)
            dumpuPL(uPLink)

        #USER OR CUSTOM URL (the trickier case, but crucial for bigger channels)
        elif isUserURL(URL):
            user = URL
            #print("GOT USER OR CUSTOM REQUEST: {}".format(user))

            #Custom URL flag
            customURL = (URL.find("www.youtube.com/c/") != -1)

            tid = getUserFromUrl(user)
            #print(customURL,tid)

            uPLink, success = getuPLink(customURL,tid)
            if not success:
                print("Failed to retrieve {}".format(tid))
            else:
                print("COMMENT THIS OUT LATER B")
                print(uPLink)
                dumpuPL(uPLink)

        #Actual video url
        else: 
            video = URL
            try:
                mkdir("out/"+video.strip())
            except:
                pass
            for lang in langs:
                jobs.put((lang, video, "default"))

    subthreads = []

    for r in range(50):
        subrunthread = Thread(target=subprrun, args=(jobs,mysession))
        subrunthread.start()
        subthreads.append(subrunthread)
        del subrunthread

    for xa in subthreads:
        xa.join() #bug (occurred once: the script ended before the last thread finished)
        subthreads.remove(xa)
        del xa