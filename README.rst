==========
Python RSI
==========


.. image:: https://img.shields.io/pypi/v/pyrsi.svg
        :target: https://pypi.python.org/pypi/pyrsi

.. image:: https://img.shields.io/travis/ExterraGroup/pyrsi.svg
        :target: https://travis-ci.org/ExterraGroup/pyrsi

.. image:: https://readthedocs.org/projects/pyrsi/badge/?version=latest
        :target: https://pyrsi.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://coveralls.io/repos/github/ExterraGroup/pyrsi/badge.svg?branch=devel
        :target: https://coveralls.io/github/ExterraGroup/pyrsi?branch=devel



Python API for interactive with the Roberts Space Industries site for Star Citizen.

.. warning:: This API is in it's very early stages and will change often.

* Free software: MIT license
* Documentation: https://pyrsi.readthedocs.io.


Features
--------

* TODO


Examples
--------

Getting system status:

.. code-block:: python

   from rsi.status import Status
   s = Status()
   current_status = s.system()
   recent_incidents = s.timeline()
   specific_incident = s.incident('28f92e5a')


Getting Roadmap information:

.. code-block:: python

    from datetime import datetime
    from rsi.roadmap import Roadmap
    r = Roadmap()
    cur_roadmap = r.fetch_roadmap(start_date=datetime(year=2021, month=1, day=1),
                                  end_date=datetime(year=2021, month=12, day=31))

Accessing ship information:

.. code-block:: python

    from rsi.shipmatrix import ShipMatrixAPI
    ship_matrix = ShipMatrixAPI()
    ship = ship_matrix.ships[170]      # ships is a dictionary, keys are ship IDs
    ship = ship_matrix.search_by_name('kraken')

Accessing citizen information:

.. code-block:: python

    from rsi.citizen import fetch_citizen
    fetch_citizen('ventorvar')

Accessing org information:

.. code-block:: python

    from rsi.org import OrgAPI
    org = OrgAPI('EXTERRA')
    member = org.members[0]

Accessing admin org information for an organization that you have the Officer or Founder role for.
This let's you see the member information for hidden members.

.. code-block:: python

    from rsi.org import OrgAPI
    org = OrgAPI('EXTERRA', admin_mode=True, username=username, password=password)
    member = org.members[0]
    members = org.search('fuzzy_handle_matching')     # list of members using fuzzy matching
    member = org.search_one('fuzzy_handle_matching')  # returns only the top match


