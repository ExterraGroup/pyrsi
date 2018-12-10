import re
import requests
from fuzzywuzzy import process
from cachetools import TTLCache
from bs4 import BeautifulSoup
from rsi import DEFAULT_RSI_URL


DEFAULT_SHIPMATRIX_ENDPOINT = '/ship-matrix/index'
DEFAULT_LOANER_MATRIX_URL = 'https://support.robertsspaceindustries.com/hc/en-us/articles/360003093114-Loaner-Ship-Matrix'
SHIP_MODEL_RE = re.compile(r"model_3d:\s*'(\S+)'")
DEFAULT_CACHE_TTL = 300
SHIP_UPGRADE_URL = 'https://robertsspaceindustries.com/pledge/ship-upgrades'
SHIP_UPGRADE_RE = re.compile(r'fromShips: (\[.*\]), toShips')


class ShipMatrixAPI(object):
    def __init__(self, rsi_url=DEFAULT_RSI_URL, api_endpoint=DEFAULT_SHIPMATRIX_ENDPOINT, cache_ttl=300,
                 enable_pledges=True, enable_ship_models=True,
                 enable_loaner_ships=True, loaner_ship_url=DEFAULT_LOANER_MATRIX_URL):
        """ Queries information from the RSI Ship Matrix.

        :argument api_endpoint The URL to use to connect to the ship matrix API
        :argument cache_ttl How long to cache the results of the API before re-querying
        """
        self.rsi_url = rsi_url.rstrip('/')
        self.api_endpoint = '{}/{}'.format(self.rsi_url, api_endpoint.lstrip('/'))
        self._enable_pledges = enable_pledges
        self._enable_ship_models = enable_ship_models
        self._enable_loaner_ships = enable_loaner_ships
        self._loaner_ship_url = loaner_ship_url
        self._ttlcache = TTLCache(maxsize=1, ttl=cache_ttl)

    def clear_cache(self):
        """ Resets the cache """
        del self._ttlcache['ships']

    def _update_cache(self):

        import os
        import json
        if os.path.exists('shipmatrix.json'):
            with open('shipmatrix.json', 'r') as f:
                data = json.load(f)
        else:

            resp = requests.get(self.api_endpoint)
            resp.raise_for_status()
            data = resp.json()

            pledge_map = {}
            if self._enable_pledges:
                try:
                    p = requests.get(SHIP_UPGRADE_URL)
                    if p.status_code == 200:
                        fromShips = SHIP_UPGRADE_RE.search(p.text)
                        if fromShips:
                            fromShips = json.loads(fromShips.groups()[0])
                            pledge_map = {_['id']: _['msrp'].strip('$').replace(',', '').replace('.00', '')
                                          for _ in fromShips}
                except Exception as e:
                    pass

            for i, ship in enumerate(_['name'] for _ in data['data']):
                # rename cargo capacity to be in line with other vars
                if 'cargocapacity' in data['data'][i]:
                    data['data'][i]['cargo_capacity'] = data['data'][i].pop('cargocapacity')

                if data['data'][i]['id'] in pledge_map:
                    data['data'][i]['pledge_cost'] = pledge_map[data['data'][i]['id']]

                if self._enable_ship_models:
                    try:
                        p = requests.get('{}{}'.format(self.rsi_url, data['data'][i]['url']))
                        if p.status_code == 200:
                            m = SHIP_MODEL_RE.search(p.text)
                            if m:
                                data['data'][i]['model_3d'] = m.group(1)
                    except Exception as e:
                        pass

            with open('shipmatrix.json', 'w') as f:
                json.dump(data, f, indent=4)

        if self._enable_loaner_ships:
            p = requests.get(self._loaner_ship_url)
            if p.status_code == 200:
                def _by_name(name):
                    return process.extractBests(name, ship_choices, score_cutoff=80)

                soup = BeautifulSoup(p.text, features='lxml')
                lis = [_.text.replace('\xa0', ' ').replace('–', '-').split(' - ')
                       for _ in soup.select('.article-body ul')[1].select('li')]
                ship_choices = {i: _['name'] for i, _ in enumerate(data['data'])}
                loaners = []
                for li in lis:
                    try:
                        li[1] = li[1].replace('Passenger', 'Personnel')
                        li[1] = li[1].split(', ') if ', ' in li[1] else [li[1]]
                        if 'Variants' in li[0] or 'Series' in li[0]:
                            li[0].replace(' &', '')
                            ships = [_[0] for _ in _by_name(li[0].split()[0])]
                            for ship in ships:
                                if ship in li[1]:
                                    continue
                                loaners.append([ship, li[1]])
                        elif '&' in li[0] or ',' in li[0]:
                            li[0] = li[0].replace(',', '&')
                            _ = [_.strip() for _ in li[0].split('&')]
                            if '-' in _[0]:
                                _[1] = '{}-{}'.format(_[0].split('-')[0], _[1])
                            else:
                                _[1] = '{} {}'.format(_[0].split()[0], _[1])
                            loaners.append([_[0], li[1]])
                            loaners.append([_[1], li[1]])
                        else:
                            loaners.append(li)
                    except Exception as e:
                        print('error parsing {}: {}'.format(li, e))

                for _ in loaners:
                    try:
                        shipid = _by_name(_[0])[0][2]
                        data['data'][shipid]['loaners'] = []
                        for loaner in _[1]:
                            data['data'][shipid]['loaners'].append(data['data'][_by_name(loaner)[0][2]])
                    except IndexError:
                        continue

        if data['msg'] == 'OK':
            self._ttlcache['ships'] = sorted(data['data'], key=lambda v: int(v['id']))

    @property
    def _cache(self):
        if 'ships' not in self._ttlcache:
            self._update_cache()
        return self._ttlcache['ships']

    def list(self):
        return self._cache

    def by_id(self, id):
        ships = [_ for _ in self.list() if _['id'] == id]
        if len(ships) == 1:
            return ships[0]
        return []

    def search_by_name(self, ship_name, score_cutoff=80, limit=None):
        """
        Return ships that match the given ship_name using fuzzy matching.

        :param ship_name: Name to match
        :param score_cutoff: minimum matching score to return
        :param limit: limit the number of matches found
        :return: List of matched results in the form of [(dict, int)] where dict is the ship data and in is the
                 matching confidence
        """
        choices = {i: _['name'] for i, _ in enumerate(self.list())}
        return [(self.list()[_[2]], _[1]) for _ in process.extractBests(ship_name, choices,
                                                                        score_cutoff=score_cutoff, limit=limit)]
