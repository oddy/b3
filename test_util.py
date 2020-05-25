
from collections import namedtuple
from six import PY2

# --- Bytes visualising helper ---

if PY2:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return ''.join([chr(int(i,16)) for i in hex_bytes_str.split()])
else:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return bytes([int(i,16) for i in hex_bytes_str.split()])

def test_sbytes():
    foo = "0a 0a 40 40 64 64"
    assert SBytes(foo) == b"\x0a\x0a\x40\x40\x64\x64"
    bar = """
    64 65 66 67 68 69 70
    71 72 73 74 75 76 77
    """
    assert SBytes(bar) == b"\x64\x65\x66\x67\x68\x69\x70\x71\x72\x73\x74\x75\x76\x77"


# --- timetuple helper for sched ---

TMX = namedtuple("tmx","tm_year tm_mon tm_mday tm_hour tm_min tm_sec tm_isdst")
def TmTime(hms_str):    return TMX(*[int(i) for i in ("0 0 0 "+hms_str+" -1").split()])
def TmDate(ymd_str):    return TMX(*[int(i) for i in (ymd_str+" 0 0 0 -1").split()])
def TmDateTime(ymdhms): return TMX(*[int(i) for i in (ymdhms+" -1").split()])

def test_tmfuncs():
    assert TmTime("13 37 20").tm_min == 37
    assert TmTime("13 37 20").tm_isdst == -1
    assert TmDate("2020 01 16").tm_year == 2020
    assert TmDateTime("2020 01 16 13 37 29").tm_mday == 16
