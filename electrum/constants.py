# -*- coding: utf-8 -*-
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2018 The Electrum developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import json


def read_json(filename, default):
    path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(path, 'r') as f:
            r = json.loads(f.read())
    except:
        r = default
    return r


class VIPSTARCOINMainnet:

    TESTNET = False
    WIF_PREFIX = 0x80
    ADDRTYPE_P2PKH = 70
    ADDRTYPE_P2SH = 50
    SEGWIT_HRP = "vips"
    GENESIS = "0000d068e1d30f79fb64446137106be9c6ee69a6a722295c131506b1ee09b77c"
    GENESIS_BITS = 0x1f00ffff
    DEFAULT_PORTS = {'t': '50001', 's': '50002'}
    DEFAULT_SERVERS = read_json('servers.json', {})
    CHECKPOINTS = read_json('checkpoints.json', {})

    BIP44_COIN_TYPE = 1919

    XPRV_HEADERS = {
        'standard': 0x0488ade4,
        'p2wpkh-p2sh': 0x049d7878,
        'p2wsh-p2sh': 0x295b005,
        'p2wpkh': 0x4b2430c,
        'p2wsh': 0x2aa7a99
    }
    XPUB_HEADERS = {
        'standard': 0x0488b21e,
        'p2wpkh-p2sh': 0x049d7cb2,
        'p2wsh-p2sh': 0x295b43f,
        'p2wpkh': 0x4b24746,
        'p2wsh': 0x2aa7ed3
    }


class VIPSTARCOINTestnet:

    TESTNET = True
    WIF_PREFIX = 0xef
    ADDRTYPE_P2PKH = 132
    ADDRTYPE_P2SH = 110
    SEGWIT_HRP = "tvips"
    GENESIS = "0000d068e1d30f79fb64446137106be9c6ee69a6a722295c131506b1ee09b77c"
    GENESIS_BITS = 0x1f00ffff
    DEFAULT_PORTS = {'t': '51001', 's': '51002'}
    DEFAULT_SERVERS = read_json('servers_testnet.json', {})
    CHECKPOINTS = read_json('checkpoints_testnet.json', {})
    BIP44_COIN_TYPE = 1

    XPRV_HEADERS = {
        'standard': 0x04358394,
        'p2wpkh-p2sh': 0x044a4e28,
        'p2wsh-p2sh': 0x024285b5,
        'p2wpkh': 0x045f18bc,
        'p2wsh': 0x02575048
    }
    XPUB_HEADERS = {
        'standard': 0x043587cf,
        'p2wpkh-p2sh': 0x044a5262,
        'p2wsh-p2sh': 0x024289ef,
        'p2wpkh': 0x045f1cf6,
        'p2wsh': 0x02575483
    }


class VIPSTARCOINRegtest(VIPSTARCOINTestnet):

    SEGWIT_HRP = "tvips"
    GENESIS = "0000d068e1d30f79fb64446137106be9c6ee69a6a722295c131506b1ee09b77c"
    DEFAULT_SERVERS = read_json('servers_regtest.json', {})
    CHECKPOINTS = {}


# don't import net directly, import the module instead (so that net is singleton)
net = VIPSTARCOINMainnet


def set_mainnet():
    global net
    net = VIPSTARCOINMainnet


def set_testnet():
    global net
    net = VIPSTARCOINTestnet


def set_regtest():
    global net
    net = VIPSTARCOINRegtest
