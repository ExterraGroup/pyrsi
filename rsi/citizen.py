import re as _re

from bs4 import BeautifulSoup as _bs
from rsi.utils import get_item
from rsi.conf import DEFAULT_RSI_URL
from rsi.session import RSISession


def fetch_citizen(name, url=DEFAULT_RSI_URL, endpoint='/citizens', skip_orgs=False, session=None):
    session = session or RSISession()
    result = {}
    url = url.rstrip('/')
    citizen_url = "{}/{}/{}".format(url.rstrip('/'), endpoint.strip('/'), name)
    orgapiurl = '{}/{}'.format(url.rstrip('/'), 'api/orgs/getOrgMembers')

    page = session.get(citizen_url)
    if page.status_code == 200:
        soup = _bs(page.text, features='html.parser')
        _ = [_.text for _ in soup.select(".info .value")[:3]]
        result['username'] = get_item(_, 0, '')
        result['handle'] = get_item(_, 1, '')
        result['title'] = get_item(_, 2, '')
        result['title_icon'] = get_item(soup.select(".info .icon img"), 0, '')
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
        result['enlisted'] = get_item(_, 'Enlisted', '')
        result['location'] = get_item(_, 'Location', '')
        result['languages'] = get_item(_, 'Fluency', '')
        result['languages'] = result['languages'].replace(',', '').split()

        if not skip_orgs:
            orgs_page = session.get("{}/organizations".format(citizen_url))
            if orgs_page.status_code == 200:
                orgsoup = _bs(orgs_page.text, features='html.parser')
                result['orgs'] = []
                for org in orgsoup.select('.orgs-content .org'):
                    orgname, sid, rank = [_.text for _ in org.select('.info .entry .value')]
                    if orgname[0] == '\xa0':
                        orgname = sid = rank = 'REDACTED'

                    roles = []
                    r = session.post(orgapiurl, data={'symbol': sid, 'search': name})
                    if r.status_code == 200:
                        r = r.json()
                        if r['success'] == 1:
                            apisoup = _bs(r['data']['html'], features='html.parser')
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
