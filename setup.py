#!/usr/bin/env python3

# python setup.py sdist --format=zip,gztar

from setuptools import setup, find_packages
import argparse
import importlib.util
import os
import platform
import sys

MIN_PYTHON_VERSION = "3.6.1"
_min_python_version_tuple = tuple(map(int, (MIN_PYTHON_VERSION.split("."))))

if sys.version_info[:3] < _min_python_version_tuple:
    sys.exit("Error: Electrum requires Python version >= %s..." % MIN_PYTHON_VERSION)

with open('./requirements.txt') as f:
    requirements = f.read().splitlines()

requirements += ['eth-hash', 'eth-utils', 'eth-abi']


# load version.py; needlessly complicated alternative to "imp.load_source":
version_spec = importlib.util.spec_from_file_location('version', 'electrum/version.py')
version_module = version = importlib.util.module_from_spec(version_spec)
version_spec.loader.exec_module(version_module)

data_files = []

if platform.system() in ['Linux', 'FreeBSD', 'DragonFly']:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root=', dest='root_path', metavar='dir', default='/')
    opts, _ = parser.parse_known_args(sys.argv[1:])
    usr_share = os.path.join(sys.prefix, "share")
    icons_dirname = 'pixmaps'
    if not os.access(opts.root_path + usr_share, os.W_OK) and \
       not os.access(opts.root_path, os.W_OK):
        icons_dirname = 'icons'
        if 'XDG_DATA_HOME' in os.environ.keys():
            usr_share = os.environ['XDG_DATA_HOME']
        else:
            usr_share = os.path.expanduser('~/.local/share')
    data_files += [
        (os.path.join(usr_share, 'applications/'), ['electrum.desktop']),
        (os.path.join(usr_share, icons_dirname), ['electrum/gui/icons/electrum.png'])
    ]

setup(
    name="VIPSTARCOIN Electrum",
    version=version.ELECTRUM_VERSION,
    python_requires='>={}'.format(MIN_PYTHON_VERSION),
    install_requires=requirements,
    extras_require={
        'full': ['Cython>=0.27', 'rlp==0.6.0', 'trezor[hidapi]>=0.9.0',
                 'keepkey', 'btchip-python', 'websocket-client', 'hidapi'],
    },
    dependency_links=[
        'https://github.com/icodeface/eth-hash',
        'https://github.com/icodeface/eth-utils',
        'https://github.com/icodeface/eth-abi',
    ],
    packages=[
        'electrum',
        'electrum.gui',
        'electrum.gui.qt',
        'electrum.plugins',
    ] + [('electrum.plugins.'+pkg) for pkg in find_packages('electrum/plugins')],
    package_dir={
        'electrum': 'electrum',
    },
    package_data={
        '': ['*.txt', '*.json', '*.ttf', '*.otf'],
        'electrum': [
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/electrum.mo',
        ],
        'electrum.gui': [
            'icons/*',
        ],
    },
    scripts=['run_electrum'],
    data_files=data_files,
    description="Lightweight VIPSTARCOIN Wallet",
    author="CodeFace",
    author_email="yuto_tetuota@yahoo.co.jp",
    license="MIT Licence",
    url="https://vipstarcoin.jp",
    long_description="""Lightweight VIPSTARCOIN Wallet"""
)
