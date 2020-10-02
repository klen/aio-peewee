import re
from os import path as op

from setuptools import setup


def _read(fname):
    try:
        return open(op.join(op.dirname(__file__), fname)).read()
    except IOError:
        return ''


meta = _read('aiopeewee.py')
install_requires = [
    line for line in _read('requirements.txt').split('\n')
    if line and not line.startswith('#')]

setup(
    name='aio-peewee',
    version=re.search(r'^version\s*=\s*"(.*)"', meta, re.M).group(1),
    license='MIT',
    description="Tools to make Peewee work when using Asyncio",
    long_description=_read('README.rst'),

    py_modules=['aiopeewee'],

    author='Kirill Klenov',
    author_email='horneds@gmail.com',
    homepage="https://github.com/klen/aio-peewee",
    repository="https://github.com/klen/aio-peewee",
    keywords="config settings configuration",

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        "Topic :: Software Development :: Libraries",
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    install_requires=install_requires,
)
