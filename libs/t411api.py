#!/usr/bin/python2.7

import requests
import sys
import os

sys.dont_write_bytecode = True

API_URL = 'https://api.t411.al'
SEARCH_URL = '/torrents/search/'


#
# Normalizes string, converts to lowercase,
# removes non-alpha characters, and converts spaces to underscores.
#
def sanitize(value):
    from re import sub
    from unicodedata import normalize
    value = normalize('NFKD', value).encode('ascii', 'ignore')
    value = sub('[^\w\s\.-]', '', value.decode('utf-8')).strip().lower()
    return sub('[-_\s]+', '_', value)


class T411API:

    def __init__(self):
        self.token = None
        self.uid = None

    #
    # Connect to the T411 service
    #
    def connect(self, username, password):
        try:
            r = requests.post(API_URL + '/auth', data={
                'username': username,
                'password': password,
            })
        except Exception as e:
            raise ValueError('Could not connect to API server: %s' % e)
        if r.status_code != 200:
            raise ValueError('Unexpected HTTP code %d upon connection' %
                             r.status_code)
        try:
            response = r.json()
        except ValueError:
            raise ValueError('Unexpected non-JSON API response : %s' %
                             r.content)

        if 'token' not in response.keys():
            raise ValueError('Unexpected T411 error : %s (%d)' %
                             (response['error'], response['code']))
        self.token = response['token']
        self.uid = int(response['uid'])

    #
    # Wraps API communication, with token and HTTP error code handling
    #
    def _raw_query(self, path, params):
        if not self.token:
            raise ValueError('You must be logged in to use T411 API')
        if not params:
            params = {}
        url = API_URL + path
        headers = {'Authorization': self.token}
        r = requests.get(url, params=params, headers=headers)
        if r.status_code != 200:
            raise ValueError('Unexpected HTTP code %d upon connection' %
                             r.status_code)
        return r

    #
    # Handle API response and errors
    #
    def _query(self, path, params=None):
        r = self._raw_query(path, params)
        try:
            response = r.json()
        except ValueError as e:
            raise ValueError('Unexpected non-JSON response from T411: %s' %
                             r.content if r else 'response is None')
        if 'error' in response:
            raise ValueError('Unexpected T411 error : %s (%d)' %
                             (response['error'], response['code']))
        return response

    #
    # Download torrent on filesystem
    #
    def download(self, torrent):
        torrent_id = torrent['id']
        details = self._query('/torrents/details/%s' % torrent_id)
        filename = sanitize(details['name'])
        base = os.getcwd()
        if not filename.endswith('.torrent'):
            filename += '.torrent'
        with open(os.path.join(base, filename), 'wb') as out:
            raw = self._raw_query('/torrents/download/%s' % torrent_id, {})
            out.write(raw.content)
        return os.path.join(base, filename)

    #
    # Search for a torrent, results are unordered
    #
    def search(self, torrent_name, params={'offset': 0, }):
        response = self._query(SEARCH_URL + torrent_name, params)
        if len(response['torrents']) == 0:
            return 0
        elif isinstance(response['torrents'][0], int):
            return 0
        return response['torrents']

    #
    # Search for a torrent, TV SHOW only
    #
    def tvshow_search(self, torrent_name, episode, season):
        params = {
            'offset': 0,
            'limit': 5,
        }
        params['cid'] = 433
        params['term[46][0]'] = 936 + episode
        params['term[47][0]'] = 967 + season
        params['term[51][0]'] = 1216
        return self.search(torrent_name, params)

    #
    # Search for a torrent, ANIME only
    #
    def anime_search(self, torrent_name, episode, season):
        params = {
            'offset': 0,
            'limit': 5,
        }
        params['cid'] = 637
        params['term[46][0]'] = 936 + int(episode)
        params['term[47][0]'] = 967 + int(season)
        return self.search(torrent_name, params)

    #
    # Get stats about an user
    #
    def user(self, uid=None):
        if not uid:
            uid = self.uid
        user = self._query('/users/profile/%d' % uid)
        if 'uid' not in user:
            user['uid'] = uid
        return user
