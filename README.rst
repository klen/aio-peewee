aio-peewee
##########

.. _description:

aio-peewee -- Use Peewee with async framework

.. _badges:

.. image:: https://github.com/klen/aio-peewee/workflows/tests/badge.svg
    :target: https://github.com/klen/aio-peewee/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/aio-peewee
    :target: https://pypi.org/project/aio-peewee/
    :alt: PYPI Version

The library doesn't make peewee work async, but allows you to use Peewee with
your asyncio based libraries correctly.

.. _features:

Features
========

- Tasks Safety. The library tracks of the connection state using
  asyncio.Task-local storage, making the Peewee Database object safe to use
  with multiple tasks inside a loop.
- Async support for connections. Connect to database asyncroniously
- Async support for Peewee Connections Pool

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

TODO

Connection Pooling
------------------

TODO

Database URL
------------

TODO


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

.. _MIT license: http://opensource.org/licenses/MIT

