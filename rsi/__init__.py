# -*- coding: utf-8 -*-

"""Top-level package for Python RSI."""
__author__ = """Ventorvar"""
__email__ = 'ventorvar@gmail.com'
__version__ = '0.1.8'


import re as _re
import requests as _requests
from bs4 import BeautifulSoup as _bs


DEFAULT_RSI_URL = 'https://robertsspaceindustries.com'


def _getitem(iterable_or_dict, index, default=None):
    """Return iterable[index] or default if IndexError is raised."""
    try:
        return iterable_or_dict[index]
    except (IndexError, KeyError):
        return default


def fetch_citizen(name, url=DEFAULT_RSI_URL, endpoint='/citizens', skip_orgs=False):
    result = {}
    url = url.rstrip('/')
    citizen_url = "{}/{}/{}".format(url.rstrip('/'), endpoint.strip('/'), name)
    orgapiurl = '{}/{}'.format(url.rstrip('/'), 'api/orgs/getOrgMembers')

    page = _requests.get(citizen_url)
    if page.status_code == 200:
        soup = _bs(page.text, features='lxml')
        _ = [_.text for _ in soup.select(".info .value")[:3]]
        result['username'] = _getitem(_, 0, '')
        result['handle'] = _getitem(_, 1, '')
        result['title'] = _getitem(_, 2, '')
        result['title_icon'] = _getitem(soup.select(".info .icon img"), 0, '')
        if result['title_icon']:
            result['title_icon'] = '{}/{}'.format(url, result['title_icon']['src'])
        result['avatar'] = "{}/{}".format(url, soup.select('.profile .thumb img')[0]['src'].lstrip('/'))
        result['url'] = citizen_url

        if soup.select('.profile-content .bio'):
            result['bio'] = soup.select('.profile-content .bio')[0].text.strip('\nBio').strip()
        else:
            result['bio'] = ''
        result['citizen_record'] = soup.select('.citizen-record .value')[0].text
        try:
            result['citizen_record'] = int(result['citizen_record'][1:])
        except:
            pass

        _ = {_.select_one('span').text:
             _re.sub(r'\s+', ' ', _.select_one('.value').text.strip()).replace(' ,', ',')
             for _ in soup.select('.profile-content > .left-col .entry')}
        result['enlisted'] = _getitem(_, 'Enlisted', '')
        result['location'] = _getitem(_, 'Location', '')
        result['languages'] = _getitem(_, 'Fluency', '')
        result['languages'] = result['languages'].replace(',', '').split()

        if not skip_orgs:
            orgs_page = _requests.get("{}/organizations".format(citizen_url))
            if orgs_page.status_code == 200:
                orgsoup = _bs(orgs_page.text, features='lxml')
                result['orgs'] = []
                for org in orgsoup.select('.orgs-content .org'):
                    orgname, sid, rank = [_.text for _ in org.select('.info .entry .value')]
                    if orgname[0] == '\xa0':
                        orgname = sid = rank = 'REDACTED'

                    roles = []
                    r = _requests.post(orgapiurl, data={'symbol': sid, 'search': name})
                    if r.status_code == 200:
                        r = r.json()
                        if r['success'] == 1:
                            apisoup = _bs(r['data']['html'], features='lxml')
                            roles = [_.text for _ in apisoup.select('.rolelist .role')]

                    orgdata = {
                        'name': orgname,
                        'sid': sid,
                        'rank': rank,
                        'roles': roles,
                    }
                    try:
                        orgdata['icon'] = '{}/{}'.format(url, org.select('.thumb img')[0]['src'].lstrip('/'))
                    except IndexError:
                        pass

                    result['orgs'].append(orgdata)
    return result
