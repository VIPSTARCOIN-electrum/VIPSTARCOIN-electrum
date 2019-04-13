VIPSTARCOIN Electrum
=====================================

  Licence: MIT Licence

  VIPSTARCOIN Electrum is a lightweight VIPSTARCOIN wallet forked from [Electrum](https://github.com/spesmilo/electrum)


Getting started
===============

For Windows and Mac OS X users, you can download latest release [here](https://github.com/VIPSTARCOIN-electrum/electrum-vips/releases).


If you are using Linux, read the "Development Version" section.


Compatible with VIPSTARCOIN mobile wallet
==================================

VIPSTARCOIN Electrum standard wallet uses [bip44](https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki) derivation path with coin_type set to 88 which not compatible with the current vipstarcoin mobile wallet.

If you want to be compatible with the vipstarcoin mobile wallet, you need to choose "VIPSTARCOIN mobile wallet compatible" to create or restore your wallet.

![](https://github.com/VIPSTARCOIN-electrum/VIPSTARCOIN-electrum/blob/master/snap/mobile_compatible.png)


Compatible with VIPSTARCOIN Qt Core wallet
==================================

If you want to import private master key from [VIPSTARCOIN Qt Core wallet](https://github.com/VIPSTARCOIN/VIPSTARCOIN/releases/), you need to choose "VIPSTARCOIN Qt Core wallet compatible" to restore your wallet.

![](https://github.com/VIPSTARCOIN-electrum/VIPSTARCOIN-electrum/blob/master/snap/qt_core_compatible.png)


Development version
===================

Check out the code from Github:

    git clone https://github.com/VIPSTARCOIN-electrum/electrum-vips.git
    cd electrum-vips

Install dependencies::

    sudo apt-get install libusb-1.0-0-dev libudev-dev
    on osx:
        brew install libusb
        
    pip3 install -r requirements.txt
    pip3 install -r requirements-binaries.txt
    pip3 install -r requirements-fixed.txt

Compile the protobuf description file:

    sudo apt-get install protobuf-compiler
    protoc --proto_path=electrum --python_out=electrum electrum/paymentrequest.proto

Create translations (optional):

    sudo apt-get install python-requests gettext

    on osx:
    brew install gettext
    brew link gettext --force

    ./contrib/make_locale

Run it:

    ./run_electrum



Creating Binaries
=================


To create binaries, create the 'packages' directory:

    ./contrib/make_packages

This directory contains the python dependencies used by Electrum.

Mac OS X
--------

See [contrib/build-osx/README.md](https://github.com/VIPSTARCOIN-electrum/VIPSTARCOIN-electrum/blob/master/contrib/build-osx/README.md) file.

Windows
-------

See [contrib/build-wine/README.md](https://github.com/VIPSTARCOIN-electrum/electrum-vips/blob/master/contrib/build-wine/README.md) file.


Linux
-----

See [contrib/build-linux/README.md](https://github.com/VIPSTARCOIN-electrum/electrum-vips/blob/master/contrib/build-linux/README.md) file.

See [gui/kivy/Readme.md](https://github.com/VIPSTARCOIN-electrum/electrum-vips/blob/master/gui/kivy/Readme.md) file.

