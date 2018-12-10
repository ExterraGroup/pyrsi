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


Python API for interactive with the Roberts Space Industries site for Star Citizen.


* Free software: MIT license
* Documentation: https://pyrsi.readthedocs.io.


Features
--------

* TODO


Examples
--------

Accessing ship information:

.. code-block:: python

    from rsi.shipmatrix import ShipMatrixAPI
    ships = ShipMatrixAPI()
    ship = ships.list()[0]
    ship = ships.search_by_name('kraken')

Accessing citizen information:

.. code-block:: python

    from rsi import fetch_citizen
    fetch_citizen('ventorvar')

Accessing org information:

.. code-block:: python

    from rsi.org import OrgAPI
    org = OrgAPI('EXTERRA')
    member = org.members[0]

