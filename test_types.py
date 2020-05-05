
from six import PY2
from hexdump import hexdump

from varint import encode_uvarint, decode_uvarint, encode_svarint, decode_svarint
from datatypes import *
from decimal import Decimal

from test_util import SBytes


# --- Basic types ---

# def test_pack_null():
#    assert PackNull(None)





def test_example():
    assert True

# def test_fail():
#     assert False


# --- Sched type ---

def test_gen_days():
    assert encode_sched(42, is_days=True)   == SBytes("80 2a")        # 42 days since epoch, days bit on, nothing else on.
    assert encode_sched(-42, is_days=True)  == SBytes("90 2a")        # pre-1970

def test_gen_sec():
    assert encode_sched(42)                 == SBytes("00 2a")        # 42 sec since epoch
    assert encode_sched(-42)                == SBytes("10 2a")        # 42 se before

def test_gen_subsec():
    assert encode_sched(42, subsec_exp=3)   == SBytes("03 2a")        # 42 milliseconds?
    assert encode_sched(42, subsec_exp=-3)  == SBytes("03 2a")        # its only ever a -ve exponent anyway so it doesnt need a sign

def test_gen_offset():
    assert encode_sched(42, offset="+0200") == SBytes("40 2a 02")
    assert encode_sched(42, offset="-0200") == SBytes("40 2a 82")
    assert encode_sched(42, offset="+0215") == SBytes("40 2a 12")
    assert encode_sched(42, offset="-0230") == SBytes("40 2a a2")
    assert encode_sched(42, offset="+0245") == SBytes("40 2a 32")
    assert encode_sched(42, offset="+1100") == SBytes("40 2a 0b")

def test_gen_tzname():
    assert encode_sched(42, tzname="Pacific/Auckland") == SBytes("20 2a b9 f8 32 9f")
    assert encode_sched(42, tzname="America/Argentina/Buenos_Aires") == SBytes("20 2a 1e 59 9d e4")

def test_gen_xmas():
    assert encode_sched(177794, is_days=True, subsec_exp=)


