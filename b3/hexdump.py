#!/usr/bin/env python
import sys
from six import PY2

colChecked = False  # do the color check on first run of hexdump, NOT on import.
colOK = False


def hexdump(src, prefix="", length=16):
    if not src:
        raise ValueError("Empty input to hexdump")
    if not isinstance(src, bytes):
        raise TypeError("Input to hexdump must be bytes, not %s" % type(src))
    CheckColorOk()

    N = 0
    result = ""
    while src:
        s, src = src[:length], src[length:]
        hexa = ""
        nccl = 0
        oldCol = None
        for x in s:
            if PY2:
                x = ord(x)  # Note: bytes accessess -> int in py3, -> str in py2.
            if colOK:
                if x in [13, 10]:
                    col = "bgrn"  # CR LF
                elif x == 32:
                    col = "bblu"  # Space
                elif 32 < x < 127:
                    col = "grn"  # printable
                else:
                    col = "rst"  # unprintable
                if col != oldCol:
                    hexa += cols[col]
                    oldCol = col

            hexa += " %02x" % x
            nccl += 3

        if colOK:
            hexa += cols["rst"]
        hexa += " " * (length * 3 - nccl)  # pad\
        s2 = dot_str_from_bytes(s)
        line = "%s%s%04X %s   %s\n" % (prefix, "  " if prefix else "", N, hexa, s2)
        result += line
        N += length

    return result.strip()


# --- Ansi Color Codes ---
# Win10 has support for ANSI sequences in its cmd terminal windows finally. This works in cmd and clink.
# Note: we dont get a tty in pytest unless pytest -s


def CheckColorOk():
    global colChecked, colOK
    if colChecked:
        return
    colChecked = True

    # try to ensure we're at interactive prompt AND not inside a repl (python / ipython)
    if (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and not hasattr(sys, "ps1")
    ):
        if not hasattr(sys, "winver"):  # linux/mac
            colOK = True
        else:
            # windows - do color only if win10 & its "does ansi if you turn it on" console
            import ctypes  # https://docs.microsoft.com/en-us/windows/console/setconsolemode

            kernel32 = ctypes.windll.kernel32
            ret = kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            #         ^^ -11 is STD_OUTPUT_HANDLE,
            #         ^^  7 is enable processed_output and VT processing
            colOK = ret != 0  # If 'turn on ansi' succeeded in windows


cols = {
    "rst": "\x1b[0m",
    "gry": "\x1b[2;37m",
    "red": "\x1b[31m",
    "yel": "\x1b[0;33m",
    "byel": "\x1b[1;33m",
    "grn": "\x1b[0;32m",
    "bgrn": "\x1b[1;32m",
    "blu": "\x1b[0;34m",
    "bblu": "\x1b[34;1m",
}

# Note: bytes accessess -> int in py3, -> str in py2.
# todo: in Go we just i > 32 && i < 127, why not just do that?
if PY2:

    def dot_str_from_bytes(s):
        return "".join([i if 31 < ord(i) < 127 else "." for i in s])

else:

    def dot_str_from_bytes(s):
        return "".join([chr(i) if 31 < i < 127 else "." for i in s])


if __name__ == "__main__":
    foo = b"hello \x01\x02\x07\x0f\x12world\nThis is a drill\034\x67\x21\x08\x09\x10\x11\x12\x13\x14 this is a drill, good morning vietnam!"
    # print(hexdump('+', b'hello world\r\nFoo Bar\xff\xff\xff\xff testing 1 2 3 is this thing on testing'))
    print(hexdump(foo))
