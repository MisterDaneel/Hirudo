#!/usr/bin/python2.7

import json
import sys
import os

sys.dont_write_bytecode = True

import libs.completer as completer

try:
    import libs.t411api as tapi
    with open('configuration.json') as configuration_file:
        configuration = json.load(configuration_file)
    search = True
except:
    search = False
try:
    import libs.my_libtorrent as trnt
except ImportError:
    raise ImportError('The package: python-libtorrent is required.')


active_torrents = {}

def download_torrent(torrent_file):
    thread = trnt.TORRENTTHREAD(torrent_file)
    thread.SetOutput(configuration["output_folder"])
    if 'leech_passkey' in configuration:
        thread.SetPasskey('T411', configuration['leech_passkey'])
    active_torrents[thread.GetTorrentName()]= thread
    thread.start()

def create_menu(title, items):
    title = 10*"*" + title + 10*"*"
    heading = len(title)*"*"
    
    print '%s\n%s\n%s'%(heading, title, heading)
    print '[ 0 ] Exit'
    for num, item in enumerate(items):
        print '[ %d ] %s'%(num+1,item)
    try:
        result = input('$ ')
        if result < len(items)+1:
            return result
    except:
        None
    return -1

def search_response(api, response):
    torrents=[]
    # Sort result by seeders and by size
    torrents = sorted(
        response['torrents'], key = lambda torrent: (
            int(torrent['seeders']),
            int(torrent['size'])),
        reverse=True)

    # Print results
    for i, t in enumerate(torrents):
        try:
            print '[ %d ] %s (seeders: %s, size: %dmo, id: %s)'\
                %(i+1, t['name'], t['seeders'], int(t['size'])/1000000, t['id'])
        except:
            None
    # Choose a result
    result = input('$ ')
    if result == 0:
        return
    elif result <= len(torrents):
        torrent_file = api.download(int(torrents[result-1]['id']))
        download_torrent(torrent_file)

def search_resquest(api):
    result = create_menu("RECHERCHE",
        ['Recherche par mots cles',
        'Recherche Serie TV',
        'Recherche Serie Anime'])
    torrent_name = raw_input('Mots cles: ') 

    if result == 0:
        return 0

    if torrent_name and result > 1:
        params = {
            'offset': 0,
            'limit': 5,
        }
        print 'tname:', torrent_name
        try:
            season = -1
            while (season < 1) or (season > 100):
                #print 'Numero de saison entre 1 et 1000'
                season = int(input('Saison: '))
            episode = -1
            while (episode < 0) or (episode > 100):
                print 'Si episode = 0: Saison complete'
                episode = int(input('Episode: '))
        except:
            result = 1

        # TV Show
        if result == 2:
            params['cid'] = 433
            params['term[46][0]'] = 936 + episode
            params['term[47][0]'] = 967 + season
            params['term[51][0]'] = 1216
            return api.advanced_search(torrent_name, params)

        # Anime
        elif result == 3:
            params['cid'] = 637
            params['term[46][0]'] = 936 + int(episode)
            params['term[47][0]'] = 967 + int(season)
            return api.advanced_search(torrent_name, params)

    # Global
    if torrent_name and result == 1:
        return api.search(torrent_name)
    return 0

def main_menu():
    if search:
        result = create_menu("MENU", ['Ouvrir un fichier torrent', 'Booster son ratio', 'See Activity', 'Rechercher sur T411'])
    else:
        result = create_menu("MENU", ['Ouvrir un fichier torrent', 'Booster son ratio', 'See Activity'])
    if result == 0:
        for torrent_name, thread in active_torrents.iteritems():
            if thread.isAlive():
                thread.Stop()

        sys.exit(0)

   
    # Open torrent file
    if result == 1:
        torrent_file = completer.raw_path('Open file:')
        download_torrent(torrent_file) 

    # Boost ratio
    elif result == 2:
        print 'to do'

    # Print activty
    elif result == 3:
        print ''
        for torrent_name, thread in active_torrents.iteritems():
            if thread.isAlive():
                thread.GetStatus()
            else:
                print '%s - COMPLETED'%torrent_name

    # Search on T411
    elif (result == 4) and search:
        while(1):
            try:
                print 'Trying to connect to T411...'
                api = tapi.T411API()
                api.connect(configuration["loginT411"], configuration["passwordT411"])
            except:
                print 'Failed to connect to T411'
                break
            print 'Succeded to connect to T411'

            response = search_resquest(api)
            if response == 0:
                break
            else:
                print 'response'
                search_response(api, response)
                break
    return

while(1):
    main_menu()
