#!/usr/bin/env python
import sys, platform
import colorama ; colorama.init()               # note this wraps sys.stdout

# --- Hexdump ---

cols = { 'rst':'\x1b[0m', 'gry':'\x1b[2;37m', 'red':'\x1b[31m', 'yel':'\x1b[0;33m', 'byel':'\x1b[1;33m',
       'grn':'\x1b[0;32m', 'bgrn':'\x1b[1;32m', 'blu':'\x1b[0;34m',  'bblu':'\x1b[34;1m' }

colOK = hasattr(sys.stdout,'isatty') and sys.stdout.isatty() # and platform.system().lower() == 'linux'

HEX_FILTER=''.join([(len(repr(chr(xz)))==3) and chr(xz) or '.' for xz in range(256)])



def hexdump(prefix, src, length=16):

    N=0; result=''
    while src:
        s,src = src[:length],src[length:]
        hexa = '' ; nccl = 0 ; oldCol = None
        for x in s:
            if x == '\r' or x == '\n':  col = 'bgrn'   # spaces: blue, ascii white, splice red, unprintables green
            elif x.isspace():           col = 'blu'
            elif repr(x)[1] == '\\':    col = 'rst'
            else:                       col = 'grn'
            if col != oldCol and colOK:
                hexa += cols[col]
                oldCol = col
            hexa += ' %02x' % ord(x) ; nccl += 3
        if colOK:         hexa += cols['rst']
        hexa += ' ' * (length*3 - nccl)     # pad
        s = s.translate(HEX_FILTER)
        result += "%s %04X %s   %s\n" % (prefix, N, hexa, s)
        N += length
    return result



if __name__ == '__main__':
    print(hexdump('',sys.stdin.read()))
