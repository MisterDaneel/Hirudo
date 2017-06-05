#!/usr/bin/python2.7
from bs4 import BeautifulSoup as bs
import cfscrape
import sys
import os

sys.dont_write_bytecode = True

SITE_URL = 'http://www.torrent9.biz'


class TORRENT9API:
    def __init__(self):
        self.scraper = cfscrape.create_scraper()

    #
    # Wraps API communication, with token and HTTP error code handling
    #
    def _raw_query(self, path):
        url = SITE_URL + path
        r = self.scraper.get(url)
        if r.status_code != 200:
            print 'Unexpected HTTP code %d upon connection' % r.status_code
        return r

    #
    # Handle API response and errors
    #
    def _query(self, path):
        r = self._raw_query(path)
        try:
            response = r.text
        except ValueError as e:
            raise ValueError('Unexpected text response from TORRENT9: %s' %
                             r.content if r else 'response is None')
        if 'error' in response:
            raise ValueError('Unexpected TORRENT9 error : %s (%d)' %
                             (response['error'], response['code']))
        return response

    #
    # Download torrent on filesystem
    #
    def download(self, torrent):
        response = self._query(torrent['href'])
        soup = bs(response, "lxml")
        attribute = soup.find('a', attrs={"class": "btn btn-danger download"})
        href = attribute.attrs.get('href')
        filename = href.split('/')[-1]
        base = os.getcwd()
        with open(os.path.join(base, filename), 'wb') as out:
            raw = self._raw_query(href)
            out.write(raw.content)
        return os.path.join(base, filename)

    #
    # Search for a torrent, results are unordered
    #
    def search(self, query):
        query = '/search_torrent/%s.html,trie-seeds-d' % query
        response = self._query(query)
        soup = bs(response, "lxml")
        table = soup.find('table',
                          attrs={"class": "table table-striped\
                                          table-bordered cust-table"})
        if table is None:
            return 0
        tbody = table.find('tbody')
        response = []
        for torrent in tbody.findAll('tr'):
            cells = torrent.findAll('td')
            attribute = cells[0].find('a')
            name = attribute.attrs.get('title')
            href = attribute.attrs.get('href')
            size = cells[1].text
            seeders = cells[2].find('span').text
            response.append({'name': name, 'href': href,
                             'size': size, 'seeders': seeders, })
        if len(response) == 0:
            return 0
        return response
