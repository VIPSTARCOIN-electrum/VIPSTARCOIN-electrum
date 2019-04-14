# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
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
import threading
import sqlite3
from typing import Optional
from . import util
from .vipstarcoin import *
from .util import print_error


blockchains = {}


def read_blockchains(config):
    global blockchains
    main_chain = Blockchain(config, 0, None)
    blockchains[0] = main_chain

    fdir = os.path.join(util.get_headers_dir(config), 'forks')
    util.make_dir(fdir)
    l = filter(lambda x: x.startswith('fork_'), os.listdir(fdir))
    l = sorted(l, key = lambda x: int(x.split('_')[1]))
    bad_chains = []
    main_chain_height = main_chain.height()
    for filename in l:
        forkpoint = int(filename.split('_')[2])
        parent_id = int(filename.split('_')[1])
        b = Blockchain(config, forkpoint, parent_id)
        if not b.is_valid():
            bad_chains.append(b.forkpoint)
        if b.parent_id == 0 and b.height() < main_chain_height - 100:
            bad_chains.append(b.forkpoint)
        blockchains[b.forkpoint] = b
    if not main_chain.is_valid():
        bad_chains.append(0)

    for bad_k in bad_chains:
        remove_chain(bad_k, blockchains)
    if len(blockchains) == 0:
        blockchains[0] = Blockchain(config, 0, None)
    return blockchains


def remove_chain(cp, chains):
    try:
        os.remove(chains[cp].path())
        del chains[cp]
        print_error('chain removed', cp)
    except (BaseException,) as e:
        print_error('remove_chain error', e)
    for k in list(chains.keys()):
        if chains[k].parent_id == cp:
            remove_chain(chains[k].forkpoint, chains)


def check_header(header):
    if type(header) is not dict:
        util.print_frames()
        print_error('[check_header] header not dic')
        return False
    for b in blockchains.values():
        if b.check_header(header):
            return b
    return False


def can_connect(header):
    for b in blockchains.values():
        if b.can_connect(header):
            return b
    return False


class Blockchain(util.PrintError):
    """
    Manages blockchain headers and their verification
    """

    verbosity_filter = 'b'

    def __init__(self, config, forkpoint, parent_id):
        self.config = config
        self.catch_up = None # interface catching up
        self.forkpoint = forkpoint
        self.checkpoints = constants.net.CHECKPOINTS
        self.parent_id = parent_id
        assert parent_id != forkpoint
        self.lock = threading.RLock()
        self.swaping = threading.Event()
        self.conn = None
        self.init_db()
        with self.lock:
            self.update_size()

    def with_lock(func):
        def func_wrapper(self, *args, **kwargs):
            with self.lock:
                return func(self, *args, **kwargs)
        return func_wrapper

    def init_db(self):
        self.conn = sqlite3.connect(self.path(), check_same_thread=False)
        cursor = self.conn.cursor()
        try:
            cursor.execute('CREATE TABLE IF NOT EXISTS header '
                           '(height INT PRIMARY KEY NOT NULL, data BLOB NOT NULL)')
            self.conn.commit()
        except (sqlite3.DatabaseError, ) as e:
            self.print_error('error when init_db', e, 'will delete the db file and recreate')
            os.remove(self.path())
            self.conn = None
            self.init_db()
        finally:
            cursor.close()

    @with_lock
    def is_valid(self):
        conn = sqlite3.connect(self.path(), check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT min(height), max(height) FROM header')
        min_height, max_height = cursor.fetchone()
        max_height = max_height or 0
        min_height = min_height or 0
        cursor.execute('SELECT COUNT(*) FROM header')
        size = int(cursor.fetchone()[0])
        cursor.close()
        conn.close()
        if not min_height == self.forkpoint:
            return False
        if size > 0 and not size == max_height - min_height + 1:
            return False
        return True

    def path(self):
        d = util.get_headers_dir(self.config)
        filename = 'blockchain_headers' if self.parent_id is None \
            else os.path.join('forks', 'fork_%d_%d'%(self.parent_id, self.forkpoint))
        return os.path.join(d, filename)

    def parent(self):
        return blockchains[self.parent_id]

    def get_max_child(self):
        children = list(filter(lambda y: y.parent_id == self.forkpoint, blockchains.values()))
        return max([x.forkpoint for x in children]) if children else None

    def get_forkpoint(self):
        mc = self.get_max_child()
        return mc if mc is not None else self.forkpoint

    def get_branch_size(self):
        return self.height() - self.get_forkpoint() + 1

    def get_name(self):
        return self.get_hash(self.get_forkpoint()).lstrip('00')[0:10]

    def fork(parent, header):
        forkpoint = header.get('block_height')
        self = Blockchain(parent.config, forkpoint, parent.forkpoint)
        self.print_error('[fork]', forkpoint, parent.forkpoint)
        self.save_header(header)
        return self

    def height(self):
        return self.forkpoint + self.size() - 1

    def size(self):
        with self.lock:
            return self._size

    def update_size(self):
        conn = sqlite3.connect(self.path(), check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM header')
        count = int(cursor.fetchone()[0])
        self._size = count
        cursor.close()

    @with_lock
    def swap_with_parent(self):
        if self.parent_id is None:
            return
        parent = self.parent()

        self.update_size()
        parent.update_size()
        parent_branch_size = parent.height() - self.forkpoint + 1
        if parent_branch_size >= self._size:
            return

        if self.swaping.is_set() or parent.swaping.is_set():
            return
        self.swaping.set()
        parent.swaping.set()

        parent_id = self.parent_id
        forkpoint = self.forkpoint

        global blockchains
        try:
            self.print_error('swap', forkpoint, parent_id)
            for i in range(forkpoint, forkpoint + self._size):
                # print_error('swaping', i)
                header = self.read_header(i, deserialize=False)
                parent_header = parent.read_header(i, deserialize=False)
                parent.write(header, i)
                if parent_header:
                    self.write(parent_header, i)
                else:
                    self.delete(i)
        except (BaseException,) as e:
            import traceback, sys
            traceback.print_exc(file=sys.stderr)
            self.print_error('swap error', e)
        # update size
        self.update_size()
        parent.update_size()
        self.swaping.clear()
        parent.swaping.clear()
        self.print_error('swap finished')
        parent.swap_with_parent()

    def write(self, raw_header, height):
        if self.forkpoint > 0 and height < self.forkpoint:
            return
        if not raw_header:
            if height:
                self.delete(height)
            else:
                self.delete_all()
            return
        with self.lock:
            self.print_error('{} try to write {}'.format(self.forkpoint, height))
            if height > self._size + self.forkpoint:
                return
            try:
                conn = self.conn
                cursor = self.conn.cursor()
            except (sqlite3.ProgrammingError, AttributeError):
                conn = sqlite3.connect(self.path(), check_same_thread=False)
                cursor = conn.cursor()
            cursor.execute('REPLACE INTO header (height, data) VALUES(?,?)', (height, raw_header))
            cursor.close()
            conn.commit()
            self.update_size()

    def delete(self, height):
        self.print_error('{} try to delete {}'.format(self.forkpoint, height))
        if self.forkpoint > 0 and height < self.forkpoint:
            return
        with self.lock:
            self.print_error('{} try to delete {}'.format(self.forkpoint, height))
            try:
                conn = self.conn
                cursor = conn.cursor()
            except (sqlite3.ProgrammingError, AttributeError):
                conn = sqlite3.connect(self.path(), check_same_thread=False)
                cursor = conn.cursor()
            cursor.execute('DELETE FROM header where height=?', (height,))
            cursor.close()
            conn.commit()
            self.update_size()

    def delete_all(self):
        if self.swaping.is_set():
            return
        with self.lock:
            try:
                conn = self.conn
                cursor = self.conn.cursor()
            except (sqlite3.ProgrammingError, AttributeError):
                conn = sqlite3.connect(self.path(), check_same_thread=False)
                cursor = conn.cursor()
            cursor.execute('DELETE FROM header')
            cursor.close()
            conn.commit()
            self._size = 0

    @with_lock
    def save_header(self, header):
        data = bfh(serialize_header(header))
        self.write(data, header.get('block_height'))
        self.swap_with_parent()

    def read_header(self, height, deserialize=True):
        assert self.parent_id != self.forkpoint
        if height < 0:
            return
        if height > self.height():
            return
        if height < self.forkpoint:
            return self.parent().read_header(height)

        conn = sqlite3.connect(self.path(), check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM header WHERE height=?', (height,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if not result or len(result) < 1:
            self.print_error('read_header 4', height, self.forkpoint, self.parent_id, result, self.height())
            self.update_size()
            return
        header = result[0]
        if deserialize:
            return deserialize_header(header, height)
        return header

    def verify_header(self, header, prev_header, bits, target):
        prev_hash = hash_header(prev_header)
        _hash = hash_header(header)
        if prev_hash != header.get('prev_block_hash'):
            raise Exception("prev hash mismatch: %s vs %s" % (prev_hash, header.get('prev_block_hash')))
        if constants.net.TESTNET:
            return True

        if bits != header.get('bits'):
            raise Exception("bits mismatch: %s vs %s, %s" %
                                (hex(bits), hex(header.get('bits')), _hash))

        if is_pos(header):
            pass
            # todo
            # 需要拿到value，?算新的target
        else:
            block_hash_as_num = int.from_bytes(bfh(_hash), byteorder='big')
            if block_hash_as_num > target:
                raise Exception(f"insufficient proof of work: {block_hash_as_num} vs target {target}")

    def check_header(self, header):
        header_hash = hash_header(header)
        height = header.get('block_height')
        real_hash = self.get_hash(height)
        return header_hash == real_hash

    @with_lock
    def save_chunk(self, index, raw_headers):
        self.print_error('{} try to save chunk {}'.format(self.forkpoint, index * CHUNK_SIZE))
        if self.swaping.is_set():
            return
        try:
            conn = self.conn
            cursor = self.conn.cursor()
        except (sqlite3.ProgrammingError, AttributeError):
            conn = sqlite3.connect(self.path(), check_same_thread=False)
            cursor = conn.cursor()

        forkpoint = self.forkpoint
        if forkpoint is None:
            forkpoint = 0
        headers = [(index * CHUNK_SIZE + i, v)
                   for i, v in enumerate(raw_headers)
                   if index * CHUNK_SIZE + i >= forkpoint]

        cursor.executemany('REPLACE INTO header (height, data) VALUES(?,?)', headers)
        cursor.close()
        conn.commit()
        self.update_size()
        self.swap_with_parent()

    def read_chunk(self, data):
        raw_headers = []
        cursor = 0
        while cursor < len(data):
            raw_header, cursor = read_a_raw_header_from_chunk(data, cursor)
            if not raw_header:
                raise Exception('read_chunk, no header read')
            raw_headers.append(raw_header)
        return raw_headers

    def verify_chunk(self, index, raw_headers):
        prev_header = None
        pprev_header = None
        if index != 0:
            prev_header = self.read_header(index * CHUNK_SIZE - 1)
            pprev_header = self.read_header(index * CHUNK_SIZE - 2)
        for i, raw_header in enumerate(raw_headers):
            height = index * CHUNK_SIZE + i
            header = deserialize_header(raw_header, height)
            bits, target = self.get_target(height, prev_header=prev_header, pprev_header=pprev_header)
            self.verify_header(header, prev_header, bits, target)
            pprev_header = prev_header
            prev_header = header

    def header_at_tip(self) -> Optional[dict]:
        """Return latest header."""
        height = self.height()
        return self.read_header(height)

    def get_hash(self, height):
        if height == -1:
            return '0000000000000000000000000000000000000000000000000000000000000000'
        elif height == 0:
            return constants.net.GENESIS
        if str(height) in self.checkpoints:
            return self.checkpoints[str(height)]
        return hash_header(self.read_header(height))

    def get_target(self, height, prev_header=None, pprev_header=None):

        if not prev_header:
            prev_header = self.read_header(height - 1)
        if not pprev_header:
            pprev_header = self.read_header(height - 2)

        if not prev_header:
            raise Exception('get header failed {}'.format(height - 1))
        if not pprev_header:
            raise Exception('get header failed {}'.format(height - 2))


        # TODO:Pythonﾁｮｯﾄﾃﾞｷﾙ人に修正してもらう

        # eHRC (enhanced Hash Rate Compensation)
        # Short, medium and long samples averaged together and compared against the target time span.
        # Adjust every block but limted to 9% change maximum.
        # Difficulty is calculated separately for PoW and PoS blocks in that PoW skips PoS blocks and vice versa.

        stake_flag = chain.get('hash_prevout_stake')
        if stake_flag is None:
            MAX_TARGET = POW_LIMIT
        else:
            MAX_TARGET = POS_LIMIT

        # params
        nTargetTimespan = 120
        DiffAdjustChange = 1000
        DiffDamping = 1000
        shortSample = 15
        mediumSample = 200
        longSample = 1000
        ShortTime = 0
        MediumTime = 0
        nActualTimespan = 0
        nActualTimespanShort = 0
        nActualTimespanMedium = 0
        nActualTimespanLong = 0
        OnelongSample = longSample + 1

        for i in range(OnelongSample):
            if pprev_header is None:
                return MAX_TARGET

        if height <= DiffAdjustChange:
            for i in range(longSample):
                if i == shortSample - 1:
                    pindexFirstShortTime = pprev_header.get('timestamp')

                if i == mediumSample - 1:
                    pindexFirstMediumTime = pprev_header.get('timestamp')

            else:
                for i in range(longSample, 0):

                    if i == shortSample - 1:
                        pindexFirstShortTime = pprev_header.get('timestamp')

                    if i == mediumSample - 1:
                        pindexFirstMediumTime = pprev_header.get('timestamp')

                    i += 1

            lastblocktime = prev_header.get('timestamp')
            firstblocktime = pprev_header.get('timestamp')

            if not lastblocktime - ShortTime == 0:
                nActualTimespanShort = (lastblocktime - ShortTime) // shortSample

            if not lastblocktime - MediumTime == 0:
                nActualTimespanMedium = (lastblocktime - MediumTime) // mediumSample

            if not lastblocktime - firstblocktime == 0:
                nActualTimespanLong = lastblocktime - firstblocktime // longSample

            nActualTimespanSum = nActualTimespanShort + nActualTimespanMedium + nActualTimespanLong

            if not nActualTimespanSum == 0:
                nActualTimespan = nActualTimespanSum // 3

            if last >= DiffDamping:
                # Apply .25 damping
                nActualTimespan = nActualTimespan + (3 * nTargetTimespan)
                nActualTimespan //= 4

            # 9% difficulty limiter
            nActualTimespanMax = nTargetTimespan * 494 // 453
            nActualTimespanMin = nTargetTimespan * 453 // 494

            nActualTimespan = max(nActualTimespan, nActualTimespanMin)
            nActualTimespan = min(nActualTimespan, nActualTimespanMax)

            bnNew = self.bits_to_target(prev_header.get('bits'))
            bnNew *= nActualTimespan
            bnNew //= nTargetTimespan

            bnNew = min(bnNew, MAX_TARGET)
            bnNew = max(bnNew, 0)

            return bnNew

    def can_connect(self, header, check_height=True):
        if not header:
            return False
        height = header['block_height']
        if check_height and self.height() != height - 1:
            self.print_error('[can_connect] check_height failed', height, self.height())
            return False
        if height == 0:
            valid = hash_header(header) == constants.net.GENESIS
            if not valid:
                print_error('[can_connect] GENESIS hash check', hash_header(header), constants.net.GENESIS)
            return valid
        prev_header = self.read_header(height - 1)
        if not prev_header:
            self.print_error('[can_connect] no prev_header', height)
            return False
        prev_hash = hash_header(prev_header)
        if prev_hash != header.get('prev_block_hash'):
            self.print_error('[can_connect] hash check failed', height)
            return False
        bits, target = self.get_target(height)
        try:
            self.verify_header(header, prev_header, bits, target)
        except BaseException as e:
            self.print_error('[can_connect] verify_header failed', e, height)
            return False
        return True

    def connect_chunk(self, idx, hexdata):
        try:
            data = bfh(hexdata)
            raw_heades = self.read_chunk(data)
            self.verify_chunk(idx, raw_heades)
            #self.print_error("validated chunk %d" % idx)
            self.save_chunk(idx, raw_heades)
            return True
        except BaseException as e:
            self.print_error('connect_chunk failed', str(e))
            return False
