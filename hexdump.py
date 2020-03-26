#!/usr/bin/env python
import sys, string
from   six import PY2

# Win10 has support for ANSI sequences in its cmd terminal windows finally. This works in cmd and clink.
# Mean we dont need colorama any more.
import ctypes
kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)  # -11 is STD_OUTPUT_HANDLE,  7 is enable processed_output and VT processing
# https://docs.microsoft.com/en-us/windows/console/setconsolemode

# --- Hexdump ---

cols = { 'rst':'\x1b[0m', 'gry':'\x1b[2;37m', 'red':'\x1b[31m', 'yel':'\x1b[0;33m', 'byel':'\x1b[1;33m',
         'grn':'\x1b[0;32m', 'bgrn':'\x1b[1;32m', 'blu':'\x1b[0;34m',  'bblu':'\x1b[34;1m' }

colOK = hasattr(sys.stdout,'isatty') and sys.stdout.isatty()
INT_PRINTABLE = [ord(i) for i in string.printable]

# Note: bytes accessess -> int in py3, -> str in py2.
# todo: in Go we just i > 32 && i < 127, why not just do that?
if PY2:
    def dot_str_from_bytes(s):
        return ''.join([i if (ord(i)>13 and i in string.printable) else '.' for i in s])
else:
    def dot_str_from_bytes(s):
        return ''.join([chr(i) if (i>13 and i in INT_PRINTABLE) else '.' for i in s])


def hexdump(src, prefix='', length=16):
    if not src:
        raise ValueError('Empty input to hexdump')
    if not isinstance(src, bytes):
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
        line = "%s%s%04X %s   %s\n" % (prefix, "  " if prefix else "", N, hexa, s2)
        result += line
        N += length

    return result.strip()


if __name__ == '__main__':
    foo = "hello world\nThis is a drill\034\x67\x21\x08\x09\x10\x11\x12\x13\x14 this is a drill, good morning vietnam!"
    #print(hexdump('+', b'hello world\r\nFoo Bar\xff\xff\xff\xff testing 1 2 3 is this thing on testing'))
    print(hexdump(foo))