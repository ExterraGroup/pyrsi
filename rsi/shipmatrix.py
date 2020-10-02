import re
import time
from collections import defaultdict
from fuzzywuzzy import process
from cachetools import TTLCache
from bs4 import BeautifulSoup
from rsi.conf import DEFAULT_RSI_URL
from rsi.session import RSISession
from rsi.pledge_store import PledgeStore
from rsi.exceptions import RSIException

DEFAULT_SHIPMATRIX_ENDPOINT = '/ship-matrix/index'
DEFAULT_LOANER_MATRIX_URL = 'https://support.robertsspaceindustries.com/hc/en-us/articles/360003093114-Loaner-Ship-Matrix'
SHIP_MODEL_RE = re.compile(r"model_3d:\s*'(\S+)'")
DEFAULT_CACHE_TTL = 300
SHIP_UPGRADE_URL = 'https://robertsspaceindustries.com/pledge/ship-upgrades'
SHIP_UPGRADE_RE = re.compile(r'fromShips: (\[.*\]), toShips')


class ShipMatrixAPI(object):
    def __init__(self, session=None, rsi_url=DEFAULT_RSI_URL, api_endpoint=DEFAULT_SHIPMATRIX_ENDPOINT, cache_ttl=300,
                 enable_pledges=True, enable_ship_models=True,
                 loaner_ship_url=DEFAULT_LOANER_MATRIX_URL):
        """ Queries information from the RSI Ship Matrix.

        :argument api_endpoint The URL to use to connect to the ship matrix API
        :argument cache_ttl How long to cache the results of the API before re-querying
        """
        self.session = session or RSISession()
        self.rsi_url = rsi_url.rstrip('/')
        self.api_endpoint = '{}/{}'.format(self.rsi_url, api_endpoint.lstrip('/'))
        self._enable_pledges = enable_pledges
        self._enable_ship_models = enable_ship_models
        self._loaner_ship_url = loaner_ship_url
        self._ttlcache = TTLCache(maxsize=3, ttl=cache_ttl)

    def clear_cache(self):
        """ Resets the cache """
        del self._ttlcache['ships_by_name']
        del self._ttlcache['ships']
        del self._ttlcache['loaners']

    def _fuzzy_choices(self):
        return {k: v['name'] for k, v in self.ships.items()}

    def _update_loaner_cache(self):
        p = self.session.get(self._loaner_ship_url)
        p.raise_for_status()

        def _lookup_by_name(name):
            return process.extractBests(name, self._fuzzy_choices(), score_cutoff=80)

        loaners = defaultdict(set)
        soup = BeautifulSoup(p.text, features='html.parser')
        for row in soup.select('.article-body table tbody tr'):
            your_ship, our_loaners = [_.text for _ in row.select('td')]
            our_loaners = [_.strip() for _ in our_loaners.split(',')]

            if your_ship in self.ships_by_name:
                ships = [your_ship]
            elif ' Series' in your_ship:
                ships = [_[0] for _ in _lookup_by_name(your_ship.replace(' Series', ''))]
            elif ' / ' in your_ship:
                ships = []
                for ship in your_ship.split(' / '):
                    ships.append(

                    )
                    ships = [_[0] for _ in _lookup_by_name(ships) if _]

            if not ships:
                print(f'WARNING [update_loaners] could not find ship for {your_ship}')
                continue

            for loaner in our_loaners:
                if loaner.lower() == 'cyclone (explorer only)':
                    for ship in ships:
                        if 'Explorer' in ship:      # handle the 6oo series
                            loaners[ship].update(['Cyclone-RN'])
                else:
                    for ship in ships:
                        loaners[ship].update([_[0] for _ in _lookup_by_name(loaner)])
        self._ttlcache['loaners'] = {k: list(v) for k, v in loaners.items()}

    def _update_ship_cache(self):
        resp = self.session.get(self.api_endpoint)
        resp.raise_for_status()
        data = resp.json()
        if data['msg'] != 'OK':
            raise RSIException(repr(data))
        data = data['data']
        data = {int(_['id']): _ for _ in data}

        pledge_map = {}
        if self._enable_pledges:
            pledges = PledgeStore(session=self.session)
            pledge_map = pledges.ship_upgrades()

        for ship_id in data.keys():
            # rename cargo capacity to be in line with other vars
            if 'cargocapacity' in data[ship_id]:
                data[ship_id]['cargo_capacity'] = data[ship_id].pop('cargocapacity')

            data[ship_id]['pledge_cost'] = pledge_map.get(ship_id, {}).get('msrp', '')
            data[ship_id]['url'] = f'{self.rsi_url}{data[ship_id]["url"]}'
            if data[ship_id]['media']:
                data[ship_id]['media'][0]['source_url'] = f'{self.rsi_url}{data[ship_id]["media"][0]["source_url"]}'
                for _ in data[ship_id]['media'][0]['images']:
                    data[ship_id]['media'][0]['images'][_] = f'{self.rsi_url}{data[ship_id]["media"][0]["images"][_]}'

            if self._enable_ship_models:
                try:
                    p = self.session.get(data[ship_id]['url'])
                    if p.status_code == 200:
                        m = SHIP_MODEL_RE.search(p.text)
                        data[ship_id]['model_3d'] = m.group(1) if m else ''
                except Exception as e:
                    print(f'WARNING: could not lookup ship model for {ship_id} ({data[ship_id]["name"]})')
        self._ttlcache['ships'] = data
        self._ttlcache['ships_by_name'] = {v['name']: v for k, v in data.items()}

    def _from_cache(self, item):
        if item == 'loaners' and 'loaners' not in self._ttlcache:
            self._update_loaner_cache()
        elif 'ships' not in self._ttlcache:
            self._update_ship_cache()
        return self._ttlcache[item]

    @property
    def loaners(self):
        return self._from_cache('loaners')

    @property
    def ships_by_name(self):
        return self._from_cache('ships_by_name')

    @property
    def ships(self):
        return self._from_cache('ships')

    def by_id(self, id):
        return self.ships[id]

    @property
    def names(self):
        return [_['name'] for _ in self.ships]

    def search_by_name(self, ship_name, score_cutoff=80, limit=None):
        """
        Return ships that match the given ship_name using fuzzy matching.

        :param ship_name: Name to match
        :param score_cutoff: minimum matching score to return
        :param limit: limit the number of matches found
        :return: List of matched results in the form of [(dict, int)] where dict is the ship data and in is the
                 matching confidence
        """
        return [(self.ships[_[2]], _[1]) for _ in process.extractBests(ship_name, self._fuzzy_choices(),
                                                                       score_cutoff=score_cutoff, limit=limit)]


if __name__ == "__main__":
    import json
    s = ShipMatrixAPI(enable_ship_models=False)
    print(len(s.ships))
    # print(json.dumps(s.ships, indent=4))
    print(json.dumps(s.loaners, indent=4))
