import re
from cachetools import TTLCache

from bs4 import BeautifulSoup
from rsi.session import RSISession
from rsi.conf import DEFAULT_RSI_URL
from rsi.exceptions import RSIException

PLEDGE_SKU_ENDPOINT = '/api/store/getSKUs'
SHIP_UPGRADE_ENDPOINT = '/pledge-store/api/upgrade'
SET_CONTEXT_TOKEN_ENDPOINT = '/pledge-store/api/setContextToken'
SHIP_UPGRADE_RE = re.compile(r'fromShips: (\[.*\]), toShips')


upgrades_initShipUpgrades_query = [{
    "operationName": "initShipUpgrade", "variables": {},
    "query": """
query initShipUpgrade {
  ships {
    id
    name
    medias {
      productThumbMediumAndSmall
      slideShow
    }
    manufacturer {
      id
      name
    }
    focus
    type
    flyableStatus
    owned
    msrp
    link
    skus {
      id
      title
      available
      price
      body
    }
  }
  manufacturers {
    id
    name
  }
  app {
    version
    env
    cookieName
    sentryDSN
    pricing {
      currencyCode
      currencySymbol
      exchangeRate
      taxRate
      isTaxInclusive
    }
    mode
    isAnonymous
    buyback {
      credit
    }
  }
}
"""}]


SKU_PRODUCT_IDS = {
    'standalone_ships': 72,
    'paints': 268,
    'gift_cards': 60,
    'addons': 3,
    'uec': 41,
    'event_tickets': 67,
    'digital_goodies': 222

}


class PledgeStore(object):
    def __init__(self, session=None, rsi_url=DEFAULT_RSI_URL, sku_endpoint=PLEDGE_SKU_ENDPOINT, cache_ttl=300,
                 ship_upgrade_endpoint=SHIP_UPGRADE_ENDPOINT, set_context_token_endpoint=SET_CONTEXT_TOKEN_ENDPOINT):
        """ Queries information from the RSI pledge store.

        :argument cache_ttl How long to cache the results of the API before re-querying
        """
        self.session = session or RSISession(url=rsi_url)
        self.rsi_url = rsi_url.rstrip('/')
        self.sku_endpoint = '{}/{}'.format(self.rsi_url, sku_endpoint.lstrip('/'))
        self.ship_upgrade_endpoint = '{}/{}'.format(self.rsi_url, ship_upgrade_endpoint.lstrip('/'))
        self._set_context_token_endpoint = '{}/{}'.format(self.rsi_url, set_context_token_endpoint.lstrip('/'))
        self._ttlcache = TTLCache(maxsize=1, ttl=cache_ttl)

        if self.session is None:
            self.session = RSISession(url=rsi_url)

    def skus(self, product_id="", search="", storefront="pledge", type="", sort='price_desc', pages=9999):
        page = 1
        opts = {"product_id": product_id, "search": search, "storefront": storefront, "type": type, "sort": sort}
        r = self.session.post(self.sku_endpoint, json={**opts, **dict(page=page)})
        r.raise_for_status()
        r = r.json()
        if not r['success']: return {}

        row_count = r['data']['rowcount']
        html = r['data']['html']
        while row_count < r['data']['totalrows'] and page < pages:
            page += 1
            r = self.session.post(self.sku_endpoint, json={**opts, **dict(page=page)})
            r.raise_for_status()
            r = r.json()
            if not r['success']: return {}
            html += r['data']['html']
            row_count += r['data']['rowcount']

        soup = BeautifulSoup(html, features='html.parser')
        for item in soup.select('div.product-item.js-ecommerce-tracking-sku'):
            try:
                yield item.select('.title')[0].text.strip(), dict(
                    title=item.select('.title')[0].text.strip(),
                    image=item.select('img')[0].get('src', ''),
                    price=item.select('.final-price')[0].get('data-value', ''),
                    price_str=item.select('.final-price')[0].text.strip(),
                    stock=item.select('.state')[0].text.strip(),
                    link=f'{self.rsi_url}{item.select(".more")[0].get("href", "")}',
                )
            except Exception as e:
                print(repr(e))

    def pledge_extras(self, product_id="", search="", *args, **kwargs):
        return self.skus(product_id, search, type="extras", *args, **kwargs)

    def pledge_game_packages(self, product_id="", search="", *args, **kwargs):
        return self.skus(product_id, search, type="game-packages")

    def ship_upgrades(self):
        pledge_map = {}
        try:
            self.session.update_session_tokens(extra=[self._set_context_token_endpoint])
            p = self.session.post(self.ship_upgrade_endpoint, json=upgrades_initShipUpgrades_query)
            if p.status_code == 200:
                p = p.json()[0]
                if p.get('errors', []):
                    raise RSIException(p['errors'])
                return {_['id']: _ for _ in p.get('data', {}).get('ships', [])}
        except Exception as e:
            raise
        return pledge_map

