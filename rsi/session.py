import codecs
import pickle
import requests
import configparser

from . import DEFAULT_RSI_URL


DEFAULT_SESSION_CONFIG = {
    'name': '',
    'id': '',
    'cookies': '',
}

RSI_SESSION_DURATION = ['session', 'day', 'week', 'month', 'year']


def cli_two_factor_prompt():
    code = input('RSI Authenticator Code: ')
    try:
        if len(code) != 6:
            raise ValueError()
        int(code)
    except ValueError:
        raise ValueError(f'Invalid code entered: {code}')
    return code


class RSISession(requests.Session):
    def __init__(self, url=DEFAULT_RSI_URL, persist_session=True, session_file='.pyrsi_session',
                 login_endpoint='/api/account/signin', login_two_factor_endpoint='/api/account/signinMultiStep',
                 session_check_endpoint='/api/contacts/list', signout_endpoint='/api/account/signout',
                 allow_two_factor=True, two_factor_prompt=cli_two_factor_prompt, two_factor_duration='session'):
        super(RSISession, self).__init__()

        self.hooks['response'].append(self._update_rsi_token)
        self.url = url.rstrip('/')

        self.login_endpoint = login_endpoint
        self.login_api = "{}/{}".format(self.url, self.login_endpoint.lstrip('/'))

        self.login_two_factor_endpoint = login_two_factor_endpoint
        self.login_two_factor_api = "{}/{}".format(self.url, self.login_two_factor_endpoint.lstrip('/'))

        self.session_check_endpoint = session_check_endpoint
        self.session_check_api = "{}/{}".format(self.url, self.session_check_endpoint.lstrip('/'))

        self.signout_endpoint = signout_endpoint
        self.signout_api = "{}/{}".format(self.url, self.signout_endpoint.lstrip('/'))

        self._allow_two_factor = allow_two_factor
        self.two_factor_prompt = two_factor_prompt
        self.two_factor_duration = two_factor_duration

        self._config = configparser.ConfigParser()
        self._config.add_section('RSI')
        self.session_file = session_file
        self.persist_session = persist_session
        self.session_name = self.session_id = ''

        if self.persist_session:
            self._load_session()

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

    def _check_api(self, api):
        resp = self.post(api)

        if resp.status_code == 200:
            info = resp.json()
            if info.get('success', 0) == 1:
                return True
        return False

    @property
    def is_authenticated(self):
        is_auth = self._check_api(self.session_check_api)
        return is_auth

    def signout(self):
        return self._check_api(self.signout_api)

    def authenticate(self, username, password):
        self._update_session(self.session_name, '')

        resp = self.post(self.login_api, json={
            'username': username,
            'password': password,
            'remember': 'off'})

        if resp.status_code != 200:
            raise Exception('Unable to log in: {}'.format(resp))

        info = resp.json()

        if info.get('code', '') == 'ErrMultiStepRequired':
            # Two factor auth required, ask user for
            if not self._allow_two_factor:
                raise Exception('Account requires Two Factor authentication which has been disabled')
            self._update_session(info['data']['session_name'], info['data']['session_id'])
            code = self.two_factor_prompt()
            resp = self.post(self.login_two_factor_api, json={
                'code': code,
                'device_name': 'pyrsi',
                'device_type': 'computer',
                'duration': self.two_factor_duration
            })
            if resp.status_code != 200:
                raise Exception('Unable to log in: {}'.format(resp))
            info = resp.json()

        if info['success'] != 1:
            raise Exception('Unable to log in: {}'.format(info))

        self._update_session(info['data']['session_name'], info['data']['session_id'])

        return True
