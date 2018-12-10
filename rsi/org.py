import time
import requests
from cachetools import TTLCache
from bs4 import BeautifulSoup

from . import DEFAULT_RSI_URL


DEFAULT_CACHE_TTL = 300


class OrgAPI(object):
    def __init__(self, symbol, url=DEFAULT_RSI_URL, endpoint='/orgs', members_endpoint='/api/orgs/getOrgMembers',
                 cache_ttl=DEFAULT_CACHE_TTL):
        self.symbol = symbol
        self.url = url.rstrip('/')
        self.endpoint = endpoint
        self.members_endpoint = members_endpoint

        self.org_url = "{}/{}/{}".format(self.url, self.endpoint.lstrip('/'), symbol)
        self.members_api = "{}/{}".format(self.url, self.members_endpoint.lstrip('/'))
        self._ttlcache = TTLCache(maxsize=1, ttl=cache_ttl)

    def clear_cache(self):
        """ Resets the cache """
        for key in self.__ttlcache.keys():
            del self._ttlcache[key]

    def _cache(self, key, update_func, *args, **kwargs):
        if key not in self._ttlcache:
            self._ttlcache[key] = update_func(*args, **kwargs)
        return self._ttlcache[key]

    def _update_members(self, search):
        members = []

        params = {
            'symbol': self.symbol,
            'search': search,
            'page': 1
        }

        # this just gets us going
        totalsize = 1

        while len(members) < totalsize:
            r = requests.post(self.members_api, data=params)
            if r.status_code == 200:
                r = r.json()
                if r is None:
                    continue

                if 'data' in r and r['data'] and 'totalrows' in r['data']:
                    totalsize = int(r['data']['totalrows'])

                if r['success'] == 1:
                    apisoup = BeautifulSoup(r['data']['html'], features='lxml')
                    for member in apisoup.select('.member-item .frontinfo .nick'):
                        members.append(member.text.strip())
                    params['page'] = params['page'] + 1
                else:
                    raise ValueError('Received error fetching Org members: {}'.format(r))
            else:
                raise Exception('Received error fetching Org members: {}'.format(r.status_code))
            time.sleep(0.5)
        return members

    def _update_details(self):
        r = requests.get(self.org_url)
        data = {}
        if r.status_code == 200:
            orgsoup = BeautifulSoup(r.text, features='lxml')
            data['banner'] = '{}{}'.format(self.url, orgsoup.select_one('.banner img')['src'])
            data['logo'] = '{}{}'.format(self.url, orgsoup.select_one('.logo img')['src'])
            data['name'], data['symbol'] = orgsoup.select_one('.inner h1').text.split(' / ')
            data['model'] = orgsoup.select_one('.inner .tags .model').text
            data['commitment'] = orgsoup.select_one('.inner .tags .commitment').text
            data['primary_focus'] = orgsoup.select_one('.inner .focus .primary img')['alt']
            data['secondary_focus'] = orgsoup.select_one('.inner .focus .secondary img')['alt']
            data['join_us'] = orgsoup.select_one('.join-us .body').text.strip()
        return data

    @property
    def members(self):
        return self._cache('members', self._update_members, search='')

    @property
    def details(self):
        return self._cache('details', self._update_details)

    @property
    def banner(self):
        return self.details['banner']

    @property
    def logo(self):
        return self.details['logo']

    @property
    def name(self):
        return self.details['name']

    @property
    def model(self):
        return self.details['model']

    @property
    def commitment(self):
        return self.details['commitment']

    @property
    def primary_focus(self):
        return self.details['primary_focus']

    @property
    def secondary_focus(self):
        return self.details['secondary_focus']

    @property
    def spectrum_url(self):
        return '{}/spectrum/community/{}'.format(self.url, self.symbol)

    @property
    def join_us(self):
        return self.details['join_us']
