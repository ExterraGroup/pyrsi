from .session import RSISession
from .pledge_store import PledgeStore
from .shipmatrix import ShipMatrixAPI
from .org import OrgAPI
from .citizen import fetch_citizen
from .status import Status


class RSISite:
    def __init__(self, session: RSISession = None, *args, **kwargs):
        self.session = session
        if self.session is None:
            self.session = RSISession(*args, **kwargs)

        self.store = PledgeStore(session=self.session)
        self.ships = ShipMatrixAPI(session=self.session)
        self.status = Status()

    @property
    def is_authenticated(self):
        return self.session.is_authenticated

    def authenticate(self, username, password, force=False):
        return self.session.authenticate(username, password, force=force)

    def citizen(self, handle, skip_orgs=False):
        return fetch_citizen(handle, skip_orgs=skip_orgs, session=self.session)

    def org(self, symbol):
        return OrgAPI(symbol=symbol, session=self.session)
