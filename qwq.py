
import socket, shlex

from hexdump import hexdump
from pprint  import pprint

def main():
    cmd = "\377\377\377\377status\x00";

    sk = socket.socket(type=socket.SOCK_DGRAM)
    sk.connect(('quake.retrolan.nz',27500))
    sk.send(cmd)
    rx = sk.recv(819)

    if rx[4] != 'n':                    # rx[4] == 'n'  means QW
        print 'Not QW server! Got:'
        print hexdump('got',rx)
        return

    rx = rx[6:]                         # skip the header, between here and \0a is key-value pairs
    first_lf = rx.find('\x0a')

    # --- Info ---
    infbuf = rx[:first_lf]
    sx = infbuf.split('\x5c')
    info = dict(zip(sx[::2],sx[1::2]))
    print '\n== Info ==\n'
    # print hexdump('settings',infbuf)
    for k,v in info.items():    print '%16s  :  %s' % (k,v)


    # --- Players ---
    playbuf = rx[first_lf+1:]
    playinfo = [[int(j) if j.isdigit() else j for j in shlex.split(i)] for i in playbuf.splitlines() if len(i) > 1]
    print '\n== Players ==\n'
    # print hexdump('players',playbuf)
    pprint(playinfo)
    # list of [player-id, frags, connect_time, ping, name, skin, shirt_color, pants_color] entries.
    print

if __name__ == '__main__':
    main()