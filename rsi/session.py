import os
import codecs
import pickle
import requests
import configparser

from rsi.conf import DEFAULT_RSI_URL

DEFAULT_SESSION_CONFIG = {
    'name': '',
    'id': '',
    'cookies': '',
}

RSI_SESSION_DURATION = ['session', 'day', 'week', 'month', 'year']

DEFAULT_API_ENDPOINTS = {
    'set_auth_token_endpoint': '/api/account/v2/setAuthToken',
    'login_endpoint': '/api/launcher/v3/signin',
    'login_two_factor_endpoint': '/api/account/signinMultiStep',
    'session_check_endpoint': '/api/launcher/v3/games/claims',
    'signout_endpoint': '/api/account/signout',
}


def cli_two_factor_prompt():
    code = input('RSI Authenticator Code: ')
    try:
        if len(code) != 6:
            raise ValueError()
        int(code)
    except ValueError:
        raise ValueError('Invalid code entered: {}'.format(code))
    return code


class RSISession(requests.Session):
    def __init__(self, url=DEFAULT_RSI_URL, persist_session=True, session_file='.pyrsi_session', clear_session=False,
                 allow_two_factor=True, two_factor_prompt=cli_two_factor_prompt, two_factor_duration='session',
                 username=None, password=None, **kwargs):
        super(RSISession, self).__init__()

        self.hooks['response'].append(self._update_rsi_token)
        self.url = url.rstrip('/')

        def _kwargs_or_default(key):
            endpoint = kwargs[key] if key in kwargs else DEFAULT_API_ENDPOINTS[key]
            return endpoint.lstrip('/')

        self._login_api = f"{self.url}/{_kwargs_or_default('login_endpoint')}"
        self._login_two_factor_api = f"{self.url}/{_kwargs_or_default('login_two_factor_endpoint')}"
        self._session_check_api = f"{self.url}/{_kwargs_or_default('session_check_endpoint')}"
        self._signout_api = f"{self.url}/{_kwargs_or_default('signout_endpoint')}"
        self._set_auth_token = f"{self.url}/{_kwargs_or_default('set_auth_token_endpoint')}"

        self._allow_two_factor = allow_two_factor
        self.two_factor_prompt = two_factor_prompt
        self.two_factor_duration = two_factor_duration

        self._config = configparser.ConfigParser()
        self._config.add_section('RSI')
        self.session_file = session_file
        self.persist_session = persist_session
        self.session_name = 'RSI-Token'
        self.session_id = ''

        if clear_session:
            self.clear_session()

        if self.persist_session:
            self._load_session()

        if username is not None and password is not None:
            self.authenticate(username, password)

    def _load_session(self):
        self._config.read(self.session_file)
        cookies = self._config.get('RSI', 'cookies', fallback='')
        if cookies:
            self.cookies.update(pickle.loads(codecs.decode(cookies.encode(), "base64")))
        self._update_session(self._config.get('RSI', 'session_name', fallback=''),
                             self._config.get('RSI', 'session_id', fallback=''),
                             save=False)

    def _update_session(self, name, id, save=True):
        if not id:
            # if id has been cleared, clear the session
            if name in self.headers:
                del self.headers[name]
            self.cookies.clear()
            self.session_name = self.session_id = ''
        else:
            self.session_name = name
            self.session_id = id
            self.headers.update({'X-{}'.format(name): id})

        self._config.set('RSI', 'session_name', name)
        self._config.set('RSI', 'session_id', id)
        self._config.set('RSI', 'cookies', codecs.encode(pickle.dumps(self.cookies), "base64").decode())
        if save and self.persist_session:
            with open(self.session_file, 'w') as f:
                self._config.write(f)

    def _update_rsi_token(self, response, *args, **kwargs):
        # called on the response hook and will update the session id from the cookie
        if self.session_name in response.cookies:
            if response.cookies[self.session_name] != self.session_id:
                self._update_session(self.session_name, self.session_id)

    def query_api(self, api, json=None):
        resp = self.post(api, json=json)
        info = {}

        if resp.status_code == 200:
            info = resp.json()
            if info.get('success', 0) == 1:
                return True, info
        return False, info

    def clear_session(self):
        if os.path.isfile(self.session_file):
            os.remove(self.session_file)

    def update_session_tokens(self, extra=[]):
        """ extra is a list of extra set*Token APIs you'd like to be hit """
        self.query_api(self._set_auth_token)
        for _ in extra:
            self.query_api(_)

    @property
    def is_authenticated(self):
        is_auth, _ = self.query_api(self._session_check_api)
        return is_auth

    def signout(self):
        success, _ = self.query_api(self._signout_api)
        self.clear_session()
        return success

    def authenticate(self, username, password, force=False):
        if not force and self.is_authenticated:
            return

        self._update_session(self.session_name, '')

        success, info = self.query_api(self._login_api, json={
            'username': username,
            'password': password,
            'remember': 'off'})

        if not success and info.get('code', '') == 'ErrMultiStepRequired':
            # Two factor auth required, ask user for
            if not self._allow_two_factor:
                raise Exception('Account requires Two Factor authentication which has been disabled')
            self._update_session(info['data']['session_name'], info['data']['session_id'])
            code = self.two_factor_prompt()
            success, info = self.query_api(self._login_two_factor_api, json={
                'code': code,
                'device_name': 'pyrsi',
                'device_type': 'computer',
                'duration': self.two_factor_duration
            })

        if not success:
            raise Exception('Unable to log in: {}'.format(info))
        self._update_session(info['data']['session_name'], info['data']['session_id'])

        return True
