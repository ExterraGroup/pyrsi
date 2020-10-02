from .session import RSISession

DEFAULT_LAUNCHER_API_ENDPOINTS = {
    'games_claims': '/api/launcher/v3/games/claims',
    'games_library': '/api/launcher/v3/games/library',
    'release': '/api/launcher/v3/games/release',
    'news': '/api/launcher/v3/content/news',
    'patch_notes': '/api/launcher/v3/content/patchNotes',
}


class LauncherAPI:
    def __init__(self, session: RSISession, **kwargs):
        self.session = session

        def _kwargs_or_default(key):
            endpoint = kwargs[key] if key in kwargs else DEFAULT_LAUNCHER_API_ENDPOINTS[key]
            return endpoint.lstrip('/')

        self._games_claims_api = f"{self.session.url}/{_kwargs_or_default('games_claims')}"
        self._games_library_api = f"{self.session.url}/{_kwargs_or_default('games_library')}"
        self._games_release = f"{self.session.url}/{_kwargs_or_default('release')}"
        self._content_news = f"{self.session.url}/{_kwargs_or_default('news')}"
        self._content_patch_notes = f"{self.session.url}/{_kwargs_or_default('patch_notes')}"

        self._games_claims = None
        self._games_library = None

    @property
    def claims(self):
        if self.session.is_authenticated:
            if self._games_claims is None:
                success, info = self.session.query_api(self._games_claims_api)
                if success:
                    self._games_claims = info['data']
            return self._games_claims
        return None

    @property
    def library(self):
        if self.claims is not None:
            if self._games_library is None:
                success, info = self.session.query_api(self._games_library_api, json={"claims": self.claims})
                if success:
                    self._games_library = info['data']
            return self._games_library
        return None

    def news(self, game_id="SC"):
        success, info = self.session.query_api(self._content_news, json={"game_id": game_id})
        if success:
            return info['data']
        raise ValueError(f'{info}')

    def patch_notes(self, game_id="SC", channel_id="LIVE"):
        success, info = self.session.query_api(self._content_patch_notes,
                                               json={"game_id": game_id, "channel_id": channel_id})
        if success:
            return info['data']
        raise ValueError(f'{info}')

    def release(self, game_id="SC", channel_id="LIVE"):
        success, info = self.session.query_api(self._games_release,
                                               json={"claims": self.claims, "gameId": game_id, "channelId": channel_id})
        if success:
            return info['data']
        raise ValueError(f'{info}')
