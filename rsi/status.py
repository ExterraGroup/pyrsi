import requests

DEFAULT_STATUS_API_URL = 'https://status.robertsspaceindustries.com/static/content/api/v0'


class Status:
    """
    Interface to the RSI status page: https://status.robertsspaceindustries.com
    """

    def __init__(self, status_api_url=DEFAULT_STATUS_API_URL, language='en'):
        self.api_url = status_api_url.rstrip('/')
        self.language = language

    def _get(self, endpoint, language, *args, **kwargs):
        lang_map = {'language': language if language is not None else self.language}
        req_url = f'{self.api_url}/{endpoint.format_map(lang_map).lstrip("/")}'
        r = requests.get(req_url, *args, **kwargs)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return {'error': {'message': 'Could not decode JSON object. Language not available or invalid URL',
                              'url': req_url}}

    def system(self, language=None):
        """
            The current system status.

            :param language:  If specified, override the set language of the `Status` for this query.
        """
        return self._get('/systems.{language}.json', language)

    def timeline(self, language=None):
        """
            The timeline of incidents for the past 7 days.

            :param language:  If specified, override the set language of the `Status` for this query.
        """
        return self._get('/incidents/timeline.{language}.json', language)

    def incident(self, incident_id, language=None):
        """
            Fetch information for a specific incident

            :param incident_id:  Unique ID for a given incident
            :param language:  If specified, override the set language of the `Status` for this query.
        """
        return self._get(f'/incidents/{incident_id}.{{language}}.json', language)
