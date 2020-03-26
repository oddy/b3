
import socket, shlex, time, os, math, textwrap

from hexdump  import hexdump
from pprint   import pprint
from operator import itemgetter

import hashlib







def rcon():

    client_time_str =  ''.join(textwrap.wrap('%08X' % (math.trunc(time.time())), 2)[::-1])

    h = hashlib.sha1()
    h.update("rcon")
    h.update(" ")
    h.update("fuckyfuck")
    h.update(client_time_str)
    h.update(" ")

    # each command, seperated by a space
    h.update("status")
    h.update(" ")

    buf = []
    buf.append("rcon")
    buf.append(" ")
    buf.append(h.hexdigest().upper())
    buf.append(client_time_str)
    buf.append(" ")

    # each command, seperated by a space
    buf.append("status")
    buf.append(" ")


    sk = socket.socket(type=socket.SOCK_DGRAM)
    sk.settimeout(2.0)
    sk.connect(('quake.retrolan.nz',27500))


    buf2 = []
    buf2.append("\xff\xff\xff\xff")
    buf2.append(''.join(buf))
    buf2.append("\x00")

    sk.send(''.join(buf2))
    rx = sk.recv(8192)

    print(hexdump(rx))



def main():
    rcon()



if __name__ == '__main__':
    main()