# -*- coding: utf-8 -*-
# version 3.2.2 - By dualB

import sys,urllib, xbmcgui, xbmcplugin, xbmcaddon,re,cache, simplejson, xbmc, parse, content
from log import log

ADDON = xbmcaddon.Addon()
ADDON_IMAGES_BASEPATH = ADDON.getAddonInfo('path')+'/resources/media/images/'
ADDON_FANART = ADDON.getAddonInfo('path')+'/fanart.jpg'

__handle__ = int(sys.argv[1])

def peupler(filtres):
    if filtres['content']['mediaBundleId']>0:
        ajouterItemAuMenu(parse.ListeVideosGroupees(filtres))
    else:
        genreId = filtres['content']['genreId']
        if genreId==-2:
            ajouterItemAuMenu(content.dictOfPopulaires(filtres))
        elif genreId>=-23 and genreId<=-21:
            log('Section populaire')
            ajouterItemAuMenu(content.get_liste_populaire(filtres))
        elif genreId!='':
            ajouterItemAuMenu(content.get_liste_emissions(filtres))
        else:
            ajouterItemAuMenu(content.dictOfMainDirs(filtres))
            ajouterItemAuMenu(content.dictOfGenres(filtres))



def ajouterItemAuMenu(items):
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_DATE)

    for item in items:
        if item['isDir'] == True:
            ajouterRepertoire(item)

        else:
            ajouterVideo(item)
            #xbmc.executebuiltin('Container.SetViewMode('+str(xbmcplugin.SORT_METHOD_DATE)+')')
            xbmc.executebuiltin('Container.SetSortDirection(0)')


def ajouterRepertoire(show):
    nom = show['nom']
    url = show['url']
    iconimage =show['image']
    genreId = show['genreId']
    resume = remove_any_html_tags(show['resume'])
    fanart = show['fanart']
    filtres = show['filtres']

    if resume=='':
        resume = urllib.unquote(ADDON.getAddonInfo('id')+' v.'+ADDON.getAddonInfo('version'))
    if ADDON.getSetting('EmissionNameInPlotEnabled') == 'true':
        resume = '[B]'+nom+'[/B][CR]'+urllib.unquote(resume)
    if iconimage=='':
        iconimage = ADDON_IMAGES_BASEPATH+'default-folder.png'

    """ function docstring """
    entry_url = sys.argv[0]+"?url="+url+\
        "&mode=1"+\
        "&filters="+urllib.quote(simplejson.dumps(filtres))

    is_it_ok = True
    liz = xbmcgui.ListItem(nom,iconImage=iconimage,thumbnailImage=iconimage)

    liz.setInfo(\
        type="Video",\
        infoLabels={\
            "Title": nom,\
            "plot":resume
        }\
    )
    setFanart(liz,fanart)

    is_it_ok = xbmcplugin.addDirectoryItem(handle=__handle__, url=entry_url, listitem=liz, isFolder=True)

    return is_it_ok

def setFanart(liz,fanart):
    if ADDON.getSetting('FanartEnabled') == 'true':
        if ADDON.getSetting('FanartEmissionsEnabled') == 'true':
            liz.setProperty('fanart_image', fanart)
        else:
            liz.setProperty('fanart_image', ADDON_FANART)
    else:
        pass


def ajouterVideo(show):
    name = show['nom']
    the_url = show['url']
    iconimage = show['image']
    url_info = 'none'
    finDisponibilite = show['endDateTxt']

    resume = remove_any_html_tags(show['resume'] +'[CR][CR]' + finDisponibilite)
    duree = show['duree']
    fanart = show['fanart']
    sourceId = show['sourceId']
    annee = show['startDate'][:4]
    premiere = show['startDate']
    episode = show['episodeNo']
    saison = show['seasonNo']

    is_it_ok = True
    entry_url = sys.argv[0]+"?url="+urllib.quote_plus(the_url)+"&sourceId="+(sourceId)

    if resume != '':
        if ADDON.getSetting('EmissionNameInPlotEnabled') == 'true':
            resume = '[B]'+name.lstrip()+'[/B]'+'[CR]'+resume.lstrip()
    else:
        resume = name.lstrip()

    liz = xbmcgui.ListItem(\
        remove_any_html_tags(name), iconImage=ADDON_IMAGES_BASEPATH+"default-video.png", thumbnailImage=iconimage)
    liz.setInfo(\
        type="Video",\
        infoLabels={\
            "Title":remove_any_html_tags(name),\
            "Plot":remove_any_html_tags(resume, False),\
            "Duration":duree,\
            "Year":annee,\
            "Premiered":premiere,\
            "Episode":episode,\
            "Season":saison}\
    )
    liz.addContextMenuItems([('Informations', 'Action(Info)')])
    setFanart(liz,fanart)
    liz.setProperty('IsPlayable', 'true')

    is_it_ok = xbmcplugin.addDirectoryItem(handle=__handle__, url=entry_url, listitem=liz, isFolder=False)
    return is_it_ok

RE_HTML_TAGS = re.compile(r'<[^>]+>')
RE_AFTER_CR = re.compile(r'\n.*')

def jouer_video(url,media_uid):
    """ function docstring """
    ref = re.split('/',url)
    refID = ref[len(ref)-1]

    # Obtenir JSON avec liens RTMP du playlistService
	
    video_json = simplejson.loads(cache.get_cached_content('https://mnmedias.api.telequebec.tv/api/v4/player/%s' % refID))
    thumbnail_url = content.getImage(video_json['imageUrlTemplate'], '320', '180')
    m3u8_pl=getStreamInfo(video_json,refID)

    # Cherche le stream de meilleure qualité
    uri = obtenirMeilleurStream(m3u8_pl)

    # lance le stream
    if uri:
        item = xbmcgui.ListItem(\
            video_json['title'],\
            iconImage=thumbnail_url,\
            thumbnailImage=thumbnail_url, path=uri)
        play_item = xbmcgui.ListItem(path=uri)
        xbmcplugin.setResolvedUrl(__handle__,True, item)
    else:
        xbmc.executebuiltin('Notification(Aucun lien disponible,Incapable d\'obtenir le lien du vidéo,5000)')
def getStreamInfo(video_json,refID):
    streams = video_json['streamInfos']
    log('STREAMS : ')
    for stream in streams:
        if stream['source']=='Limelight':
            return m3u8LL(refID)
        elif stream['source']=='Brightcove':
            return m3u8BC(stream['sourceId'])

def getPolicyKey():
    # hardcoded, in case...
    key = 'BCpkADawqM3lBz07fdV6Q__Z8jM6RenArMfaM8YoxyIBexztP2lLBvXw2PlknyXbnK_1MMSmXw7qKqOM9mPI-doKvmqeywTJ3wKVzhdJSQN8JthhhmrUT5zVikMU8OvQEGirR-e7e7iqmZSC'
    
    try:
        data = cache.get_cached_content('https://players.brightcove.net/6150020952001/default_default/config.json',True)
        key = simplejson.loads(data)['video_cloud']['policy_key']

    except Exception:
        log('ERREUR, impossible de récupérer dynamiquement la Policy Key.')
        return key
    return key

def m3u8BC(media_uid):
    log('BRIGHTCOVE : %s' % media_uid)
    key = getPolicyKey()
    header = {'key':'Accept','value':'application/json;pk=%s'%key }
    a= cache.get_cached_content('https://bcovlive-a.akamaihd.net/86e93a0ab79047e1b216e2b0a1ac5363/us-east-1/%s/playlist.m3u8' % media_uid,True,[header])
    return a

def m3u8LL(refID):
    return cache.get_cached_content('https://mnmedias.api.telequebec.tv/m3u8/%s.m3u8' % refID,True)


def remove_any_html_tags(text, crlf=True):
    """ function docstring """
    try:
        text = RE_HTML_TAGS.sub('', text)
        text = text.lstrip()
        if crlf == True:
            text = RE_AFTER_CR.sub('', text)
        return text
    except Exception:
        return ''

def obtenirMeilleurStream(pl):
    maxBW = 0
    bandWidth=None
    uri = None
    res = None
    maxres = int(ADDON.getSetting("MaxResolution"))
    for line in pl.split('\n'):
        if re.search('#EXT-X',line):
            bandWidth = None
            try:
                match = re.search(r'BANDWIDTH=(\d+)',line)
                bandWidth = int(match.group(1))
            except :
                bandWidth = None
            res = None
            try:
                match = re.search(r'RESOLUTION=\d+x(\d+)',line)
                res = int(match.group(1))
            except :
                res = None
        elif line.startswith('http'):
            if bandWidth != None:
                if bandWidth > maxBW:
                    if res != None and res <= maxres:
                        maxBW = bandWidth
                        uri = line
    return uri
