aio-peewee
##########

DeprecationWarning
-------------------

**The package is deprecated. Please use `peewee-aio <https://github.com/klen/peewee-aio>`_ instead.**

---

.. _description:

**aio-peewee** -- Peewee support for async frameworks (Asyncio_, Trio_, Curio_)

.. _badges:

.. image:: https://github.com/klen/aio-peewee/workflows/tests/badge.svg
    :target: https://github.com/klen/aio-peewee/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/aio-peewee
    :target: https://pypi.org/project/aio-peewee/
    :alt: PYPI Version

.. image:: https://img.shields.io/pypi/pyversions/aio-peewee
    :target: https://pypi.org/project/aio-peewee/
    :alt: Python Versions

.. _important:

    The library doesn't make peewee work async, but allows you to use Peewee with
    your asyncio based libraries correctly.

.. _features:

Features
========

- Tasks Safety. The library tracks of the connection state using Task-local
  storage, making the Peewee Database object safe to use with multiple tasks
  inside a loop.
- Async management of connections for Peewee Connections Pool

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.8

.. _installation:

Installation
=============

**aio-peewee** should be installed using pip: ::

    pip install aio-peewee

.. _usage:

QuickStart
==========

.. code:: python

    from aiopeewee import db_url

    db = db_url.connect('postgres+async://locahost:5432/database')

    async def main(id=1):
        async with db:
            item = Model.get(Model.id == 1)

        return item.name


Usage
=====


Initialization
--------------

.. code:: python

   from aiopeewee import PostgresqlDatabaseAsync, SqliteDatabaseAsync, MySQLDatabaseAsync, CockroachDatabaseAsync

    db = PostgresqlDatabaseAsync('my_app', user='app', password='db_password', host='10.1.0.8', port=3306)


Async Connect
-------------

.. code:: python

   # Manual
   async def main():
        await db.connect_async()
        # ...
        await db.close_async()

    # Context manager
   async def main():
        async with db:
            # ...


Connection Pooling
------------------

.. code:: python

   from aiopeewee import PooledPostgresqlDatabaseAsync, PooledSqliteDatabaseAsync, PooledMySQLDatabaseAsync, PooledCockroachDatabaseAsync

   db = PooledPostgresqlDatabaseAsync('my_database', max_connections=8, stale_timeout=300, user='postgres')


Database URL
------------

.. code:: python

   from aiopeewee import db_url

    db0 = db_url.connect('cockroachdb+async://localhost/db', **db_params)
    db1 = db_url.connect('cockroachdb+pool+async://localhost/db', **db_params)
    db2 = db_url.connect('mysql+async://localhost/db', **db_params)
    db3 = db_url.connect('mysql+pool+async://localhost/db', **db_params)
    db4 = db_url.connect('postgres+async://localhost/db', **db_params)
    db5 = db_url.connect('postgres+pool+async://localhost/db', **db_params)
    db6 = db_url.connect('sqlite+async://localhost/db', **db_params)
    db7 = db_url.connect('sqlite+pool+async://localhost/db', **db_params)
    db8 = db_url.connect('sqliteexc+async://localhost/db', **db_params)
    db9 = db_url.connect('sqliteexc+pool+async://localhost/db', **db_params)


ASGI Middleware
---------------

.. code:: python

    import datetime as dt

    from asgi_tools import App
    from aiopeewee import PeeweeASGIPlugin
    import peewee as pw


    db = PeeweeASGIPlugin(url='sqlite+async:///db.sqlite')


    @db.register
    class Visit(pw.Model):
        created = pw.DateTimeField(default=dt.datetime.utcnow())
        address = pw.CharField()


    db.create_tables()


    app = App()


    @app.route('/')
    async def visits_json(request):
        """Store the visit and load latest 10 visits."""
        Visit.create(address=request.client[0])
        return [{
            'id': v.id, 'address': v.address, 'timestamp': round(v.created.timestamp()),
        } for v in Visit.select().order_by(Visit.id.desc()).limit(10)]


    app = db.middleware(app)


Curio
-----

``aio-peewee`` uses ``contextvars`` to store db connections. So you have to
enable ``contextvars`` for Curio:
https://curio.readthedocs.io/en/latest/howto.html#how-do-you-use-contextvars


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/aio-peewee/issues

.. _contributing:

Contributing
============

Development of the project happens at: https://github.com/klen/aio-peewee

.. _license:

License
========

Licensed under a `MIT license`_.


.. _links:


.. _klen: https://github.com/klen
.. _Asyncio: https://docs.python.org/3/library/asyncio.html
.. _Trio: https://trio.readthedocs.io/en/stable/index.html
.. _Curio: https://github.com/dabeaz/curio

.. _MIT license: http://opensource.org/licenses/MIT

