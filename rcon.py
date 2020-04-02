
import socket, shlex, time, os, math, textwrap

from hexdump  import hexdump
from pprint   import pprint
from operator import itemgetter

import hashlib

# INNER "rcon space password         client_time_hex space command space command space"  etc
# OUTER "rcon space hex(sha1(INNER)) client_time_hex space command space command space" etc

password = 'fred'

def rcon_pkt(cmdline):
    client_time_hex = ''.join(textwrap.wrap('%08X' % (math.trunc(time.time())), 2)[::-1])
    before = "rcon "
    after  = client_time_hex + " " + cmdline.strip() + " "

    inner  = before + password + after
    inner_hash = hashlib.sha1(inner).hexdigest().upper()
    outer  = before + inner_hash + after

    pkt = "\xff\xff\xff\xff" + outer + "\x00"
    return pkt



def RconCmd(cmdline):
    sk = socket.socket(type=socket.SOCK_DGRAM)
    sk.settimeout(0.1)
    sk.connect(('quake.retrolan.nz',27500))

    buf = rcon_pkt(cmdline)

    print(hexdump(buf))

    sk.send(buf)
    rx = sk.recv(8192)
    return rx

    # print(hexdump(rx))
    # print
    # always returns ff ff ff ff 6e, then (mostly)text. (00 on the end)
    # the id numbers in status response are weird because they're colored
    # and my oddity name is unprintables as

    # rx = rx[5:]
    # print(rx)

def main():
    rx = RconCmd("status")
    print(hexdump(rx))
    print
    print rx[5:]



if __name__ == '__main__':
    main()