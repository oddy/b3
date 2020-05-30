
# -*- coding: UTF-8 -*-

from test_util import SBytes
from type_basic import *

def test_base_null_enc():
    assert encode_null(None) == b""

def test_base_null_dec():
    assert decode_null(b"", 0, 0) == (None, 0)


def test_base_bool_enc():
    assert encode_bool(True)    == SBytes("01")
    assert encode_bool(False)   == SBytes("00")

def test_base_bool_dec():
    assert decode_bool(SBytes("01"),0,1) == (True, 1)
    assert decode_bool(SBytes("00"),0,1) == (False,1)


TESTB = b"hello"
def test_base_bytes_enc():
    assert encode_bytes(TESTB) == TESTB
def test_base_bytes_dec():
    assert decode_bytes(TESTB,0,len(TESTB)) == (TESTB, len(TESTB))


#
# BMP 0000-FFFF,  SMP 10000-1FFFF,  SIP 20000-2FFFF,  TIP 30000-3FFFF
# Went and got the utf8 bytes from the equivalent golang script
TEST_UNISTRS = (
    ( u"hello world", SBytes("68 65 6c 6c 6f 20 77 6f 72 6c 64") ),
    ( u"Виагра",      SBytes("d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0") ),                                 # Viagra OWEN
    ( u"✈✉🚀🚸🚼🚽", SBytes("e2 9c 88 e2 9c 89 f0 9f 9a 80 f0 9f 9a b8 f0 9f 9a bc f0 9f 9a bd") ),   # SMP
)

def test_base_utf8_enc():
    for tstr,tbytes in TEST_UNISTRS:
        assert encode_utf8(tstr)   == tbytes

def test_base_utf8_dec():
    for tstr,tbytes in TEST_UNISTRS:
        assert decode_utf8(tbytes,0,len(tbytes)) == (tstr,len(tbytes))


TEST_INT64S = (
    ( 123456789,  SBytes("15 cd 5b 07 00 00 00 00") ),
    ( -123456789, SBytes("eb 32 a4 f8 ff ff ff ff") ),

)

def test_base_int64_enc():
    for tint,tbytes in TEST_INT64S:
        assert encode_int64(tint) == tbytes


def test_base_int64_dec():
    for tint,tbytes in TEST_INT64S:
        assert decode_int64(tbytes,0,8) == (tint, 8)




