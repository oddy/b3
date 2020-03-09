#!/usr/bin/env python
import sys, string
from   six import PY2
import colorama ; colorama.init()               # note this wraps sys.stdout

# --- Hexdump ---

cols = { 'rst':'\x1b[0m', 'gry':'\x1b[2;37m', 'red':'\x1b[31m', 'yel':'\x1b[0;33m', 'byel':'\x1b[1;33m',
         'grn':'\x1b[0;32m', 'bgrn':'\x1b[1;32m', 'blu':'\x1b[0;34m',  'bblu':'\x1b[34;1m' }

colOK = hasattr(sys.stdout,'isatty') and sys.stdout.isatty()

# Note: bytes accessess -> int in py3, -> str in py2.
if PY2:
    def dot_str_from_bytes(s):
        return ''.join([i if (ord(i)>13 and i in string.printable) else '.' for i in s])
else:
    INT_PRINTABLE = [ord(i) for i in string.printable]

    def dot_str_from_bytes(s):
        return ''.join([chr(i) if (i>13 and i in INT_PRINTABLE) else '.' for i in s])


def hexdump(prefix, src, length=16):
    if src and not isinstance(src, bytes):
        raise TypeError('Input to hexdump must be bytes, not %s' % type(src))
    N=0; result=''
    while src:
        s,src = src[:length],src[length:]
        hexa = '' ; nccl = 0 ; oldCol = None
        for x in s:
            if PY2:     x = ord(x)          # Note: bytes accessess -> int in py3, -> str in py2.
            if colOK:
                if x == 13 or x == 10:                      col = 'bgrn'        # CR LF
                elif x == 32:                               col = 'bblu'        # Space
                elif x>13 and chr(x) in string.printable:   col = 'grn'         # printable
                else:                                       col = 'rst'         # unprintable
                if col != oldCol:
                    hexa += cols[col]
                    oldCol = col

            hexa += ' %02x' % x ; nccl += 3

        if colOK:
            hexa += cols['rst']
        hexa += ' ' * (length*3 - nccl)     # pad\
        s2 = dot_str_from_bytes(s)
        result += "%s %04X %s   %s\n" % (prefix, N, hexa, s2)
        N += length

    return result.strip()


if __name__ == '__main__':
    print(hexdump('a', b'hello world'))

    #print(hexdump('',sys.stdin.read()))
