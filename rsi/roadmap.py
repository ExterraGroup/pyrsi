from datetime import datetime

from rsi.session import RSISession
from rsi.conf import DEFAULT_RSI_URL
from rsi.exceptions import RSIException

ROADMAP_ENDPOINT = '/graphql'

DATE_STR_FMT = "%Y-%m-%d"
roadmap_query = [{
    "operationName": "Roadmap",
    "variables": {"startDate": "", "endDate": ""},
    "query": """

query Roadmap($startDate: String!, $endDate: String!, $context: String) {
  roadmap(startDate: $startDate, endDate: $endDate, context: $context) {
    ...Team
    deliverables {
      ...Deliverable
      projects {
        ...Project
        __typename
      }
      timeAllocations {
        ...TimeAllocation
        discipline {
          ...Discipline
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment Team on Team {
  title
  description
  __typename
}

fragment Deliverable on Deliverable {
  title
  description
  startDate
  endDate
  __typename
}

fragment Project on Project {
  title
  logo
  __typename
}

fragment TimeAllocation on TimeAllocation {
  startDate
  endDate
  __typename
}

fragment Discipline on Discipline {
  title
  color
  countMembers
  __typename
}
"""
}]


class Roadmap(object):
    def __init__(self, session=None, rsi_url=DEFAULT_RSI_URL, roadmap_endpoint=ROADMAP_ENDPOINT):
        """ Queries information from the RSI Roadmap

        :argument cache_ttl How long to cache the results of the API before re-querying
        """
        self.session = session or RSISession(url=rsi_url)
        self.rsi_url = rsi_url.rstrip('/')
        self.roadmap_endpoint = '{}/{}'.format(self.rsi_url, roadmap_endpoint.lstrip('/'))

        if self.session is None:
            self.session = RSISession(url=rsi_url)

    def fetch_roadmap(self, start_date: datetime, end_date: datetime):
        """

        :param start_date: Datetime beginning of the roadmap to search for
        :param end_date: Datetime end of the roadmap to search for
        :return: diction of roadmap entries
        """
        q = roadmap_query.copy()
        q[0]['variables'].update({
            'startDate': start_date.strftime(DATE_STR_FMT),
            'endDate': end_date.strftime(DATE_STR_FMT)
        })
        try:
            p = self.session.post(self.roadmap_endpoint, json=q)
            if p.status_code == 200:
                p = p.json()[0]
                if p.get('errors', []):
                    raise RSIException(p['errors'])
                return p.get('data', {}).get('roadmap', [])
        except Exception as e:
            raise
        return []
