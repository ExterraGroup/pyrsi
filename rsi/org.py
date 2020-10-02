import time
from fuzzywuzzy import process
from cachetools import TTLCache
from bs4 import BeautifulSoup

from rsi.conf import DEFAULT_RSI_URL
from .session import RSISession


DEFAULT_CACHE_TTL = 300


class OrgAPI(object):
    def __init__(self, symbol, session=None, admin_mode=False, url=DEFAULT_RSI_URL, endpoint='/orgs',
                 members_endpoint='/api/orgs/getOrgMembers', cache_ttl=DEFAULT_CACHE_TTL):
        self.symbol = symbol
        self.url = url.rstrip('/')
        self.endpoint = endpoint
        self.members_endpoint = members_endpoint
        self.admin_mode = admin_mode
        self.session = session or RSISession(url=url)

        self.org_url = "{}/{}/{}".format(self.url, self.endpoint.lstrip('/'), symbol)
        self.members_api = "{}/{}".format(self.url, self.members_endpoint.lstrip('/'))
        self._ttlcache = TTLCache(maxsize=1, ttl=cache_ttl)

        self._update_details()   # pull and cache the org details which will raise 404 if not found

    def clear_cache(self):
        """ Resets the cache """
        for key in self._ttlcache.keys():
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

        if self.admin_mode:
            params['admin_mode'] = 1

        # this just gets us going
        totalsize = 1
        members_scanned = 0

        while members_scanned < totalsize:
            r = self.session.post(self.members_api, data=params)

            if r.status_code == 200:
                r = r.json()
                if r is None:
                    continue

                if 'data' in r and r['data'] and 'totalrows' in r['data']:
                    totalsize = int(r['data']['totalrows'])

                if r['success'] == 1:
                    apisoup = BeautifulSoup(r['data']['html'], features='html.parser')
                    for member in apisoup.select('.member-item'):
                        members_scanned += 1
                        if member.select('.member-visibility-restriction'):
                            print('skipping hidden member')
                            continue

                        members.append({
                            'name': member.select_one('.name').text,
                            'handle': member.select_one('.nick').text,
                            'avatar': '{}{}'.format(self.url, member.select_one('img').attrs['src']),
                            'affiliate': member.select_one('.title').text == 'Affiliate',
                            'rank': member.select_one('.rank').text,
                            'roles': [_.text for _ in member.select('.rolelist .role')],
                            'url': '{}{}'.format(self.url, member.select_one('a.membercard').attrs['href']),

                            # defaults for things online admins will be able to get the real values of
                            'id': '',
                            'visibility': 'Membership: Visible',
                            'last_online': '',
                        })

                        if self.admin_mode:
                            members[-1].update({
                                'id': member.attrs.get('data-member-id', ''),
                                'last_online': member.select_one('.frontinfo .lastonline').text,
                                'visibility': member.select_one('.frontinfo .visibility').text,
                            })

                    params['page'] = params['page'] + 1
                else:
                    raise ValueError('Received error fetching Org members: {}'.format(r))
            else:
                raise Exception('Received error fetching Org members: {}'.format(r.status_code))
            time.sleep(0.5)
        return members

    def _update_details(self):
        r = self.session.get(self.org_url)
        data = {}
        r.raise_for_status()

        orgsoup = BeautifulSoup(r.text, features='html.parser')
        data['banner'] = '{}{}'.format(self.url, orgsoup.select_one('.banner img')['src'])
        data['logo'] = '{}{}'.format(self.url, orgsoup.select_one('.logo img')['src'])
        data['name'], data['symbol'] = orgsoup.select_one('.inner h1').text.split(' / ')
        data['model'] = orgsoup.select_one('.inner .tags .model').text
        data['commitment'] = orgsoup.select_one('.inner .tags .commitment').text
        data['primary_focus'] = orgsoup.select_one('.inner .focus .primary img')['alt']
        data['secondary_focus'] = orgsoup.select_one('.inner .focus .secondary img')['alt']
        data['join_us'] = orgsoup.select_one('.join-us .body').text.strip()
        return data

    def search(self, handle, score_cutoff=80, limit=None):
        """
        Return members that match the given handle using fuzzy matching.

        :param handle: Handle to match
        :param score_cutoff: minimum matching score to return
        :param limit: limit the number of matches found
        :return: List of matched results in the form of [(dict, int)] where dict is the ship data and in is the
                 matching confidence
        """
        choices = {i: _['handle'] for i, _ in enumerate(self.members)}
        return [(self.members[_[2]], _[1]) for _ in process.extractBests(handle, choices,
                                                                         score_cutoff=score_cutoff, limit=limit)]

    def search_one(self, handle):
        """
        Return the first member that matches the given handle using fuzzy matching, or None

        :param handle: Handle to match
        :return: The best matching member, or None
        """
        choices = self.search(handle, limit=1)
        if choices:
            return choices[0][0]
        return None

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
