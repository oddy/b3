
# -*- coding: UTF-8 -*-

from b3.utils import SBytes
from b3.type_basic import *

# Note: these above break with ImportError No module named b3, UNLESS i make the tests a package by adding an empty __init__.py
# Note: once i do that, then everything seems to work perfectly. I think this is pytest magic, not sure.

def test_base_bool_enc():
    assert encode_bool(True)   == SBytes("01")
    assert encode_bool(False)  == b""                       # compact zero-value mode

def test_base_bool_dec():
    assert decode_bool(SBytes("01"),0,1) is True
    assert decode_bool(SBytes("00"),0,1) is False           # normal zero-value
    assert decode_bool(SBytes(""),0,0)   is False           # compact zero-value mode


# BMP 0000-FFFF,  SMP 10000-1FFFF,  SIP 20000-2FFFF,  TIP 30000-3FFFF
# Went and got the utf8 bytes from the equivalent golang script
TEST_UNISTRS = (
    ( u"hello world", SBytes("68 65 6c 6c 6f 20 77 6f 72 6c 64") ),
    ( u"Виагра",      SBytes("d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0") ),                                 # Viagra OWEN
    ( u"✈✉🚀🚸🚼🚽", SBytes("e2 9c 88 e2 9c 89 f0 9f 9a 80 f0 9f 9a b8 f0 9f 9a bc f0 9f 9a bd") ),   # SMP
    ( u"", b"")                                                         # zero-length strings
)

def test_base_utf8_enc():
    for tstr,tbytes in TEST_UNISTRS:
        assert encode_utf8(tstr)   == tbytes

def test_base_utf8_dec():
    for tstr,tbytes in TEST_UNISTRS:
        assert decode_utf8(tbytes,0,len(tbytes)) == tstr


TEST_INT64S = (
    ( 123456789,  SBytes("15 cd 5b 07 00 00 00 00") ),
    ( -123456789, SBytes("eb 32 a4 f8 ff ff ff ff") ),
    (0,           SBytes("") ),                                      # compact zero-value mode
)


def test_base_int64_enc():
    for tint,tbytes in TEST_INT64S:
        assert encode_int64(tint) == tbytes


def test_base_int64_dec():
    for tint,tbytes in TEST_INT64S:
        assert decode_int64(tbytes,0,len(tbytes)) == tint
    assert decode_int64(SBytes("00 00 00 00 00 00 00 00"),0,8) == 0     # check non-compact zero value too



TEST_FLOAT64S = (
    ( 12345.6789,   SBytes("a1 f8 31 e6 d6 1c c8 40") ),
    ( 0.0,          SBytes("")),                                    # compact zero-value mode
)

def test_base_float64_enc():
    for tflo,tbytes in TEST_FLOAT64S:
        assert encode_float64(tflo) == tbytes

def test_base_float64_dec():
    for tflo,tbytes in TEST_FLOAT64S:
        assert decode_float64(tbytes,0,len(tbytes)) == tflo
    assert decode_float64(SBytes("00 00 00 00 00 00 00 00"),0,8) == 0.0     # check non-compact zero value too


# stamp64 is signed, so it's 2**63 ns / 1000 / 1000 / 1000 / 60 / 60 / 24 / 365 = about 292.5 years each side of 1970
# which is about yr 1678 - 2262
# Operationally the same as int64 itself. Except with an optional float conversion on the encoder side.
timNano = 1590845636168000000
timFlo  = 1590845636.168
timZero = 0

def test_base_stamp64_enc():
    assert encode_stamp64(timFlo)  == SBytes("00 22 46 6c ad d1 13 16")
    assert encode_stamp64(timNano) == SBytes("00 22 46 6c ad d1 13 16")
    assert encode_stamp64(timZero) == SBytes("")

def test_base_stamp64_dec():
    assert decode_stamp64(SBytes("00 22 46 6c ad d1 13 16"),0,8) == timNano
    assert decode_stamp64(SBytes(""),0,0)                        == timZero     # compact zero-value mode
    assert decode_stamp64(SBytes("00 00 00 00 00 00 00 00"),0,8) == timZero    # non-compact zero value too


tcplx = 13.37+42.42j
tcplx_bytes = SBytes("3d 0a d7 a3 70 bd 2a 40 f6 28 5c 8f c2 35 45 40")

def test_base_complex_enc():
    assert encode_complex(tcplx) == tcplx_bytes
    assert encode_complex(0j) == SBytes("")

def test_base_complex_dec():
    assert decode_complex(tcplx_bytes, 0, 16) == tcplx
    assert decode_complex(SBytes(""),0,0) == 0j
    assert decode_complex(SBytes("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"),0,16) == 0j



