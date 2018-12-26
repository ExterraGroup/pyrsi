import requests

from . import DEFAULT_RSI_URL


class RSISession(requests.Session):
    def __init__(self, url=DEFAULT_RSI_URL, login_endpoint='/api/account/signin'):
        super(RSISession, self).__init__()

        self.hooks['response'].append(self._update_rsi_token)
        self.url = url.rstrip('/')
        self.login_endpoint = login_endpoint
        self.login_api = "{}/{}".format(self.url, self.login_endpoint.lstrip('/'))

    def _update_rsi_token(self, response, *args, **kwargs):
        if 'Rsi-Token' in response.cookies:
            self.headers['X-Rsi-Token'] = response.cookies['Rsi-Token']

    def authenticate(self, username, password):
        resp = self.post(self.login_api, json={
            'username': username,
            'password': password,
            'remember': 'off'})

        if resp.status_code != 200:
            raise Exception('Unable to log in: {}'.format(resp))

        info = resp.json()
        if info['success'] != 1:
            raise Exception('Unable to log in: {}'.format(info))

        self.headers.update({'X-{}'.format(info['data']['session_name']): info['data']['session_id']})
