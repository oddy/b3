
from six import PY2
from hexdump import hexdump

from varint import encode_uvarint, decode_uvarint, encode_svarint, decode_svarint
from datatypes import *
from decimal import Decimal

from test_util import SBytes

from   collections import namedtuple

from type_sched import encode_sched, encode_sched_dt

# --- Basic types ---

# def test_pack_null():
#    assert PackNull(None)



def test_example():
    assert True


# def test_fail():
#     assert False

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


# --- Sched type ---



def test_gen_date():
    assert encode_sched(TmDate("2020 01 16"), True, False)      == SBytes("80 c8 1f 01 10")
def test_gen_time():
    assert encode_sched(TmTime("13 37 20"), False, True)        == SBytes("40 0d 25 14")
def test_gen_date_time():
    assert encode_sched(TmDateTime("2020 01 16 13 37 20"), True, True) == SBytes("c0 c8 1f 01 10 0d 25 14")
def test_gen_offset():
    assert encode_sched(None, False, False, offset="+0200") == SBytes("10 02")
    assert encode_sched(None, False, False, offset="-0200") == SBytes("10 82")
    assert encode_sched(None, False, False, offset="+0215") == SBytes("10 12")
    assert encode_sched(None, False, False, offset="-0230") == SBytes("10 a2")
    assert encode_sched(None, False, False, offset="+0245") == SBytes("10 32")
    assert encode_sched(None, False, False, offset="+1100") == SBytes("10 0b")
def test_gen_offset_dst():
    assert encode_sched(TMX(0,0,0,0,0,0, 0),  False, False, offset="+0200") == SBytes("10 02")
    assert encode_sched(TMX(0,0,0,0,0,0, 1),  False, False, offset="+0200") == SBytes("10 42")
    assert encode_sched(TMX(0,0,0,0,0,0, -1), False, False, offset="+0200") == SBytes("10 02")



# def test_gen_days():
#     assert encode_sched(42, is_days=True)   == SBytes("80 2a")        # 42 days since epoch, days bit on, nothing else on.
#     assert encode_sched(-42, is_days=True)  == SBytes("90 2a")        # pre-1970
#
# def test_gen_sec():
#     assert encode_sched(42)                 == SBytes("00 2a")        # 42 sec since epoch
#     assert encode_sched(-42)                == SBytes("10 2a")        # 42 se before
#
# def test_gen_subsec():
#     assert encode_sched(42, subsec_exp=3)   == SBytes("03 2a")        # 42 milliseconds?
#     assert encode_sched(42, subsec_exp=-3)  == SBytes("03 2a")        # its only ever a -ve exponent anyway so it doesnt need a sign
#
#
# def test_gen_tzname():
#     assert encode_sched(42, tzname="Pacific/Auckland")               == SBytes("20 2a b9 f8 32 9f")
#     assert encode_sched(42, tzname="America/Argentina/Buenos_Aires") == SBytes("20 2a 1e 59 9d e4")
#
# def test_gen_xmas():
#     assert encode_sched(-177794, is_days=True, subsec_exp=9, offset="-1045", tzname="Fred") == SBytes("f9 82 ed 0a ba 60 5e 1b 9a")






