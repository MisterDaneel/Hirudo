#!/usr/bin/python2.7

import json
import sys
import os

sys.dont_write_bytecode = True

with open('configuration.json') as configuration_file:
    configuration = json.load(configuration_file)
try:
    import libs.t411api as t411api
    import libs.torrent9api as t9api
    search = True
except:
    search = False
try:
    import libs.my_libtorrent as trnt
except ImportError:
    raise ImportError('The package: python-libtorrent is required.')


active_torrents = {}

def download_torrent(torrent_file):
    torrent_file = torrent_file.decode('utf8')
    thread = trnt.TORRENTTHREAD(torrent_file)
    thread.SetOutput(configuration["output_folder"])
    if 'leech_passkey' in configuration:
        thread.SetPasskey(configuration['user_passkey'], configuration['leech_passkey'])
    active_torrents[thread.GetTorrentName()]= thread
    thread.start()

def create_menu(title, items):
    title = 10*"*" + title + 10*"*"
    heading = len(title)*"*"
    
    while True:
        print '%s\n%s\n%s'%(heading, title, heading)
        print '[ 0 ] Exit'
        for num, item in enumerate(items):
            print '[ %d ] %s'%(num+1,item)
        try:
            result = input('$ ')
            if result < len(items)+1:
                return result
        except:
            continue

def search_response(api, response):
    torrents=[]
    # Sort result by seeders and by size
    torrents = sorted(
        response, key = lambda torrent: (
            int(torrent['seeders'])),
            reverse=True)
    # Print results
    for i, torrent in enumerate(torrents):
        try:
            print '[ %d ] %s (seeders: %s, size: %dmo)'\
                %(i+1, torrent['name'], torrent['seeders'], int(torrent['size'])/1000000)
        except:
            print '[ %d ] %s (seeders: %s, size: %s)'\
                %(i+1, torrent['name'], torrent['seeders'], torrent['size'])
    # Choose a result
    #try:
    result = input('$ ')
    if result == 0:
        return
    elif result <= len(torrents):
        torrent_file = api.download(torrents[result-1])
        download_torrent(torrent_file)
    #except:
    #    None

def search_resquest(api):
    result = create_menu("RECHERCHE",
        ['Recherche par mots cles',
        'Recherche Serie TV',
        'Recherche Serie Anime'])

    if result == 0:
        return 0

    torrent_name = raw_input('Mots cles: ') 

    if  torrent_name == '':
        return 0

    if torrent_name and result > 1:
        try:
            season = -1
            while (season < 1) or (season > 100):
                season = int(input('Saison: '))
            episode = -1
            while (episode < 0) or (episode > 100):
                print 'Si episode = 0: Saison complete'
                episode = int(input('Episode: '))
        except:
            result = 1

        # TV Show
        if result == 2:
            return api.tvshow_search(torrent_name, episode, season)

        # Anime
        elif result == 3:
            return api.anime_search(torrent_name, episode, season)

    # Global
    elif torrent_name and result == 1:
        return api.search(torrent_name)
    return 0

def main_menu():
    if search:
        result = create_menu("MENU",
            ['Ouvrir un fichier torrent', 
            'See Activity', 
            'Rechercher sur T411',
            'Rechercher sur Torrent9'
            #'Booster son ratio', 
        ])
    else:
        result = create_menu("MENU", ['Ouvrir un fichier torrent', 'See Activity'])
    if result == 0:
        for torrent_name, thread in active_torrents.iteritems():
            if thread.isAlive():
                thread.Stop()

        sys.exit(0)
   
    # Open torrent file
    if result == 1:
        try:
            import libs.completer as completer
            torrent_file = completer.raw_path('Open file:')
        except:
            torrent_file = raw_input('Open file:')
        download_torrent(torrent_file) 

    # Print activty
    elif result == 2:
        print ''
        for torrent_name, thread in active_torrents.iteritems():
            if thread.isAlive():
                thread.GetStatus()
            else:
                print '%s - COMPLETED'%torrent_name

    # Search on T411
    elif (result == 3) and search:
        while(1):
            try:
                print 'Trying to connect to T411...'
                api = t411api.T411API()
                api.connect(configuration["loginT411"], configuration["passwordT411"])
            except Exception as e:
                print 'Failed to connect to T411: %s'%e
                break
            print 'Succeded to connect to T411'
            response = search_resquest(api)
            if response == 0:
                print 'Pas de resultats.'
            else:
                search_response(api, response)
            break
    # Search on Torrent9
    elif (result == 4) and search:
        while(1):
            api = t9api.TORRENT9API()
            response = search_resquest(api)
            if response == 0:
                print 'Pas de resultats.'
            else:
                search_response(api, response)
            break
    return

while(1):
    main_menu()
