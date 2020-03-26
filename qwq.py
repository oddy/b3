
import socket, shlex, time, os

from hexdump  import hexdump
from pprint   import pprint
from operator import itemgetter

class PrintTable(object):
    def __init__(s):
        s.max_field_lens = {}        
        s.data = []
    def AddLine(s, field_list):
        f2 = [str(i) for i in field_list]
        s.data.append(f2)
        for i,f in enumerate(f2):
            if len(f) > s.max_field_lens.get(i,0):
                s.max_field_lens[i] = len(f)        
    def Output(s):
        g = []
        for line in s.data:
            x = [ f.rjust(s.max_field_lens[i]+1) for i,f in enumerate(line) ]
            g.append('|'.join(x))
        return '\n'.join(g)


def ping():
    cmd = "\377\377\377\377status\x00";

    sk = socket.socket(type=socket.SOCK_DGRAM)
    sk.settimeout(2.0)
    sk.connect(('quake.retrolan.nz',27500))
    sk.send(cmd)
    rx = sk.recv(819)

    if rx[4] != 'n':                    # rx[4] == 'n'  means QW
        print 'Not QW server! Got:'
        print hexdump('got',rx)
        return

    rx = rx[6:]                         # skip the header, between here and \0a is key-value pairs
    first_lf = rx.find('\x0a')

    # --- Players ---
    playbuf = rx[first_lf+1:]

    # list of [player-id, frags, connect_time, ping, name, skin, shirt_color, pants_color] entries.
    playinfo = [[int(j) if j.isdigit() else j for j in shlex.split(i)] for i in playbuf.splitlines() if len(i) > 1]    
    playinfo = sorted(playinfo, key=itemgetter(1), reverse=True)

    T = PrintTable()
    T.AddLine(['ID','Frags','Time','Ping','Name','Skin','shirt','pants'])
    for player in playinfo:
        T.AddLine(player)        

    #print '\n== Players ==\n'
    print T.Output()


    # --- Info ---
    infbuf = rx[:first_lf]
    sx = infbuf.split('\x5c')
    info = dict(zip(sx[::2],sx[1::2]))
    #print '\n== Info ==\n'
    # print hexdump('settings',infbuf)
    # for k,v in info.items():    print '%16s  :  %s' % (k,v)           # all info
    print
    for k in ['status','map','fraglimit','timelimit']:
        print '%16s  :  %s' % (k,info[k])


def main():
    while True:
        time.sleep(1.0)
        os.system('cls')
        try:
            ping()
        except Exception as e:
            print("ERROR:",str(e))




if __name__ == '__main__':
    main()