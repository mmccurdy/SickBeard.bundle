import os

####################################################################################################

VIDEO_PREFIX = "/video/sickbeard"

NAME = L('SickBeard')

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
SEARCH_ICON = 'icon-search.png'
PREFS_ICON  = 'icon-prefs.png'
SB_URL      = 'http://'+Prefs['sbIP']+':'+Prefs['sbPort']
PLEX_URL    = 'http://'+Prefs['plexIP']+':32400'
TV_SECTION  = ""

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('SickBeard'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    HTTP.CacheTime=3600*3
    if Prefs['sbUser'] and Prefs['sbPass']:
        HTTP.SetPassword(url=SB_URL, username=Prefs['sbUser'], password=Prefs['sbPass'])

    global TV_SECTION
    TV_SECTION = GetTvSectionID()
    if TV_SECTION == "":
        return MessageContainer('SickBeard Plugin', L('Unable to locate Plex library TV metadata. Check Plugin Prefs.'))

####################################################################################################

def MainMenu():
    dir = MediaContainer(viewGroup="InfoList")

    dir.Append(Function(DirectoryItem(ComingEpisodes,"Coming Episodes","Soon to be aired",
            summary="See which shows that you follow have episodes airing soon",thumb=R(ICON),art=R(ART))))
    dir.Append(Function(DirectoryItem(ShowList,"All Shows","SickBeard List",
            summary="See details about all shows which SickBeard manages for you",thumb=R(ICON),art=R(ART))))
    dir.Append(Function(InputDirectoryItem(SearchResults,"Add Show","Add new show to SickBeard",
            summary="Search by name to add a new show to SickBeard's watch list",thumb=R(SEARCH_ICON),art=R(ART))))
    dir.Append(PrefsItem(title="Preferences",subtitle="SickBeard plugin prefs",
        summary="Set SickBeard plugin preferences to allow it to connect to SickBeard app",thumb=R(PREFS_ICON)))

    return dir

####################################################################################################

def ComingEpisodes(sender):
    dir = MediaContainer(ViewGroup='InfoList', title2='Coming Episodes')
    url = SB_URL + '/comingEpisodes'
    episodesPage = HTML.ElementFromURL(url, errors='ignore')
    
    for episode in episodesPage.xpath('//div[@class="listing"]'):
        showName    = episode.xpath('a')[0].get('name')
        #Log('Found: '+ showName)
        airsNext    = episode.xpath('div/p[1]/span')[1].text
        timeSlot    = episode.xpath('div/p[2]/span')[3].text
        updateUrl   = episode.xpath('.//a[@class="forceUpdate"]')[0].get('href')
        #Log(updateUrl)
        dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu,title=showName,subtitle="Airs: "+timeSlot,
            summary="Next episode: "+airsNext, thumb=Function(GetThumb, showName=showName)),url=updateUrl))
    
    return dir

####################################################################################################

def SearchResults(sender,query):
    dir = MediaContainer(ViewGroup="InfoList",title2="Search Results")
    
    #tell SickBeard to create the folder in the TV directory
    newShowFolder = String.Quote(Prefs['tvDir']+'/'+query, usePlus=True)
    Log(newShowFolder)
    addFolderUrl = SB_URL+'/home/addShows/addShows/?showDirs='+newShowFolder
    url = SB_URL + '/home/addShows/searchTVDBForShowName?name=' + String.Quote(query, usePlus=True)
    
    addFolderResult = HTTP.Request(addFolderUrl).content
    tvdbResult = JSON.ObjectFromURL(url).get("results")
    
    for item in tvdbResult:
        tvdbID = item[0]
        showName = item[1]
        startDate = item[2]
        if startDate == None:
            startDate = "Unknown"
        Log("Found: " +showName)
        dir.Append(Function(DirectoryItem(AddShow,title=showName,subtitle="TVDB: "+str(tvdbID),
            summary="First aired: "+startDate),name=showName,ID=tvdbID))
    
    return dir
    
####################################################################################################  

def  ShowList(sender):
    '''List all shows that SickBeard manages, and relevant info about each show'''
    dir = MediaContainer(ViewGroup="InfoList", title2="All Shows")
    url = SB_URL + '/home/'
    showsPage = HTML.ElementFromURL(url, errors='ignore')
    for show in showsPage.xpath('//tr[@class="evenLine"]'):
        #try:
        next    = show.xpath('td')[0].text
        if next == None:
            next = "unknown"
        #Log('Next airs: '+next)
        name    = show.xpath('td[2]//text()')[0]
        #Log(name)
        link  = show.xpath('td[2]/a')[0].get('href')
        #Log(link)
        showID = str(link)[-5:]
        #Log(showID)
        network = show.xpath('td')[2].text
        if network == None:
            network = "unknown"
        #Log('Network: '+network)
        quality = str(show.xpath('td')[3].text)[2:]
        #Log('Download quatlity: '+quality)
        episodes = str(show.xpath('td[5]/comment()')[0])[4:-3]
        #Log(episodes)
        status  = show.xpath('td')[6].text
        if status == None:
            status = "Not Available"
        #Log("Status: "+status)
        showSummary = GetSummary(name)
        if showSummary == None:
            showSummary = "Not available"
        if status == "Continuing":
            info    = ('Next Episode: ' + str(next) + '\n' +
                    'Airs on: ' + network + '\n' +
                    'Status: ' + status + '\n' +
                    'Download quality: ' + quality + '\n' +
                    'Summary: ' + showSummary)
        else:
            info    = ('Aired on: ' + network + '\n' +
                    'Status: ' + status + '\n' +
                    'Download quality: ' + quality + '\n' +
                    'Summary: ' + showSummary)
        #except:
        #    pass
        updateUrl = '/home/updateShow?show=' + showID +'&force=1'
        dir.Append(Function(PopupDirectoryItem(SeriesSelectMenu, title=name, subtitle='Episodes: '+episodes,
            summary=info, thumb=Function(GetThumb, showName=name)), showID=showID, showName=name))
    return dir
    
####################################################################################################    

def SeriesSelectMenu(sender, showID, showName):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    dir = MediaContainer(title='')
    dir.Append(Function(PopupDirectoryItem(EpisodeList, title="View Episode List"), showID=showID, showName=showName))
    dir.Append(Function(PopupDirectoryItem(ForceRefresh, title="Force search for this series"), showID=showID))
    
    return dir
    
####################################################################################################

def EpisodeSelectMenu(sender, url):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    dir = MediaContainer(title='')
    dir.Append(Function(PopupDirectoryItem(ForceRefresh, title="Force search for this episode"), url=url))
    
    return dir
    
####################################################################################################

def ForceRefresh(sender, showID):
    '''tell SickBeard to do a force search for the given episode/series'''
    updateUrl = SB_URL + '/home/updateShow?show=' + showID +'&force=1'
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

#################################################################################################### 

def AddShow(sender, name, ID):
    '''Tell SickBeard to add the given show to the watched/wanted list'''
    dir = MessageContainer("SickBeard", L('Show added to list'))
    if str(Prefs['tvDir'])[-1] == '/':
        postValues = {'whichSeries' : str(ID), 'skipShow' : "0", 'showToAdd' : String.Quote(Prefs['tvDir']+name, usePlus=True)}
    else:
        postValues = {'whichSeries' : str(ID), 'skipShow' : "0", 'showToAdd' : String.Quote(Prefs['tvDir']+'/'+name, usePlus=True)}
    url = SB_URL + '/home/addShows/addSingleShow'
    Log(postValues['showToAdd'])
    redirect = HTTP.Request(url, postValues).content
    
    #Log(str(result))
    
    return dir
    
####################################################################################################

def GetThumb(showName):
    '''retrieve the thumbnail image from the Plex metadata database based on the title of the series'''

    tv_section_url = PLEX_URL + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore')
    try:
        seriesThumb = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('thumb')
        data = HTTP.Request(PLEX_URL + seriesThumb, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return Redirect(R(ICON))

####################################################################################################

def GetTvSectionID():
    '''Determine what section(s) are TV series in Plex library'''
    
    library = HTML.ElementFromURL(PLEX_URL+'/library/sections')
    sectionID = library.xpath('//directory[@title="'+Prefs['tvSection']+'"]')[0].get('key')
    Log('TV section ID: ' + sectionID)
    return sectionID
    
####################################################################################################

def GetSummary(showName):
    '''retrieve the series summary from the Plex metadata database based on the title of the series'''

    tv_section_url = PLEX_URL + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore', cacheTime=CACHE_1MONTH)
    try:
        summary = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('summary')
    except:
        summary = "Not found."
    
    return summary

####################################################################################################

def EpisodeList(sender, showID, showName):
    '''Display alist of all episodes of the given TV series including the SickBeard state of each'''
    episodeListUrl = SB_URL + '/home/displayShow?show=' + showID
    dir = MediaContainer(ViewGroup='InfoList', title2=showName)
    #seriesThumb = GetThumb(showName)
    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore')
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        else:
            epNum = episode.xpath('.//a')[0].get('name')
            #Log('Found: ' + epNum)
            epTitle = str(episode.xpath('./td')[4].text)[10:-10]
            #Log('Title: ' + epTitle)
            epDate = episode.xpath('./td')[5].text
            #Log('AirDate: ' + epDate)
            epStatus = episode.xpath('./td')[7].text
            #Log('Status: ' + epStatus)
            if epStatus != 'Skipped':
                epSearchUrl = episode.xpath('.//a')[1].get('href')
                #Log('Link: '+epSearchUrl)
            dir.Append(Function(PopupDirectoryItem(EpisodeMenu, title=epNum+' '+epTitle, subtitle='Status: '+epStatus,
                summary="Airdate: "+epDate, thumb=Function(GetThumb, showName=showName))))
        
    return dir

####################################################################################################

def EpisodeMenu():
    return