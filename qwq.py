
import socket, shlex, time, os, traceback, sys, textwrap, hashlib
import operator, math
from   hexdump  import hexdump
from   operator import itemgetter
from   pprint import pprint


"""
#define	S2C_CHALLENGE		'c'
#define	S2C_CONNECTION		'j'
#define	A2A_PING			'k'	// respond with an A2A_ACK
#define	A2A_ACK				'l'	// general acknowledgement without info
#define	A2A_NACK			'm'	// [+ comment] general failure
#define A2A_ECHO			'e' // for echoing
#define	A2C_PRINT			'n'	// print a message on client

#define	S2M_HEARTBEAT		'a'	// + serverinfo + userlist + fraglist
#define	A2C_CLIENT_COMMAND	'B'	// + command line
#define	S2M_SHUTDOWN		'C'
"""

# ======================================================================================================================
# = TOOLKIT
# ======================================================================================================================

class AttrDict(dict):
    def __getattr__(self, name):
        return self[name]

play_fields = ['pid','frags','time','ping','name','skin','shirt','pants']

class QwServer(object):
    def __init__(s, addr, port, passw=None):
        s.addr = addr
        s.port = port
        s.password = passw
        s.sk = socket.socket(type=socket.SOCK_DGRAM)
        s.sk.settimeout(0.5)
        s.sk.connect((addr,port))

    # --- Info ping query ---

    def Status(s):
        s.sk.send(b"\xff\xff\xff\xffstatus\x00")
        rx = s.sk.recv(1500)
        if rx[4] not in [b'n', 0x6e]:            # Expecting #define A2C_PRINT 'n' (py2 'n', py3 0x6e
            print(hexdump(rx))
            raise TypeError(u"Not QW Server!")

        rx = rx[6:]                         # skip the header, between here and \0a is key-value pairs
        first_lf = rx.find('\x0a')
        print(hexdump(rx))
        print("first_lf = ",first_lf, " len = ",len(rx))

        set_buf = rx[:first_lf]
        sx = set_buf.split('\x5c')

        settings = AttrDict(dict(zip(sx[::2], sx[1::2])))
        pprint(settings)

        # list of [player-id, frags, connect_time, ping, name, skin, shirt_color, pants_color] entries.
        playbuf = rx[first_lf+1:]           # player info after first LF
        # print("Player buf:")
        # print(hexdump(playbuf))
        playinfo = [[int(j) if j.replace('-','').isdigit() else j for j in shlex.split(i)] for i in playbuf.splitlines() if len(i) > 1]
        playinfo = sorted(playinfo, key=itemgetter(1), reverse=True)
        players = [AttrDict(dict(zip(play_fields, play_ent))) for play_ent in playinfo]

        return settings, playinfo, players

    # --- Rcon Command ---

    # INNER "rcon space password         client_time_hex space command space command space"  etc
    # OUTER "rcon space hex(sha1(INNER)) client_time_hex space command space command space" etc

    def Rcon(s, cmdline):
        client_time_hex = ''.join(textwrap.wrap('%08X' % (math.trunc(time.time())), 2)[::-1])
        before = "rcon "
        after  = client_time_hex + " " + cmdline.strip() + " "
        print('before   ',before.__class__)
        print('after    ',after.__class__)
        print('password ',s.password.__class__)
        inner  = before + s.password + after
        inner_hash = hashlib.sha1(inner).hexdigest().upper()
        outer  = before + inner_hash + after
        pkt = "\xff\xff\xff\xff" + bytes(outer) + "\x00"
        s.sk.send(pkt)
        rx = s.sk.recv(8192)
        return rx



# ======================================================================================================================
# = TESTING
# ======================================================================================================================


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


def TotFrags(players):
    ret = 0
    for i in players:
        ret += i.frags
    return ret


def PrintSettings(settings):
    # for k,v in settings.items():
    #   print '%16s  :  %s' % (k,v)           # all info
    for k in ['status','map','fraglimit','timelimit']:
        print('%16s  :  %s' % (k,settings[k]))

def PrintPlayinfo(playinfo):
    T = PrintTable()
    T.AddLine([i.title() for i in play_fields])
    for player in playinfo:
        T.AddLine(player)
    #print '\n== Players ==\n'
    print(T.Output())

mode = 0

def main():
    omap = '' ; mode = 0
    if 'mode1' in sys.argv:
        mode = 1
    rcon_password = open('rcon_password.txt','rb').read().strip()

    qw = QwServer('quake.retrolan.nz', 27500, rcon_password)
    while True:
        try:
            settings, playinfo, players = qw.Status()

            if mode == 0:
                PrintPlayinfo(playinfo)
                print("")
                PrintSettings(settings)
                print("")
                print(TotFrags(players))

                z = qw.Rcon("say frag count: %i" % (TotFrags(players)))
                print("Rcon returns")
                print(hexdump(z))

            if mode == 1:
                if settings.map != omap:
                    print('Map change: ',settings.map)
                    ofrags = 0
                    omap = settings.map
                frags = TotFrags(players)
                print(frags-ofrags,"  ",) ; sys.stdout.flush()
                ofrags = frags

            time.sleep(1.0)

            if mode == 0:
                os.system('cls')
        except Exception as e:
            print("ERROR:",str(e))
            print(traceback.format_exc())
            time.sleep(1.0)




if __name__ == '__main__':
    main()