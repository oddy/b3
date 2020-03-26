
import socket, shlex, time, os, math, textwrap

from hexdump  import hexdump
from pprint   import pprint
from operator import itemgetter

import hashlib


# INNER "rcon space password         client_time_hex space command space command space"  etc
# OUTER "rcon space hex(sha1(INNER)) client_time_hex space command space command space" etc


def rcon_pkt(password, *cmds):



    client_time_hex = ''.join(textwrap.wrap('%08X' % (math.trunc(time.time())), 2)[::-1])    
    before = "rcon "
    after  = client_time_hex + " " + " ".join(cmds) + " "

    inner  = before + password + after
    inner_hash = hashlib.sha1(inner).hexdigest().upper()
    outer  = before + inner_hash + after

    pkt = "\xff\xff\xff\xff" + outer + "\x00"
    return pkt


def rcon2():
    sk = socket.socket(type=socket.SOCK_DGRAM)
    sk.settimeout(2.0)
    sk.connect(('quake.retrolan.nz',27500))


    buf = rcon_pkt("fuckyfuck", "map", "ukooldm4")
    #buf = rcon_pkt("fuckyfuck", "status")

    sk.send(buf)
    rx = sk.recv(8192)

    print(hexdump(rx))
    print
    # always returns ff ff ff ff 6e, then (mostly)text. (00 on the end)
    # the id numbers in status response are weird because they're colored
    # and my oddity name is unprintables as

    rx = rx[5:]
    print(rx)








# def rcon():

#     client_time_str =  ''.join(textwrap.wrap('%08X' % (math.trunc(time.time())), 2)[::-1])

#     h = hashlib.sha1()
#     h.update("rcon")
#     h.update(" ")
#     h.update("fuckyfuck")
#     h.update(client_time_str)
#     h.update(" ")

#     # each command, seperated by a space
#     h.update("status")
#     h.update(" ")

#     buf = []
#     buf.append("rcon")
#     buf.append(" ")
#     buf.append(h.hexdigest().upper())
#     buf.append(client_time_str)
#     buf.append(" ")

#     # each command, seperated by a space
#     buf.append("status")
#     buf.append(" ")


#     sk = socket.socket(type=socket.SOCK_DGRAM)
#     sk.settimeout(2.0)
#     sk.connect(('quake.retrolan.nz',27500))


#     buf2 = []
#     buf2.append("\xff\xff\xff\xff")
#     buf2.append(''.join(buf))
#     buf2.append("\x00")

#     sk.send(''.join(buf2))
#     rx = sk.recv(8192)

#     print(hexdump(rx))



def main():
    rcon2()



if __name__ == '__main__':
    main()