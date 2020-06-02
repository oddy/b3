
# -*- coding: UTF-8 -*-

from utils import SBytes
from item_header import *


def test_header_key_enc_none_int():
    assert encode_key(None)         == (0x00, b"")
    assert encode_key(4)            == (0x40, SBytes("04"))               # py2 int
    assert encode_key(7777777777)   == (0x40, SBytes("f1 f0 dd fc 1c"))   # py2 long

def test_header_key_dec_none_int():
    assert decode_key(0x00, b"", 0)                         == (None, 0)
    assert decode_key(0x40, SBytes("04"), 0)                == (4, 1)
    assert decode_key(0x40, SBytes("f1 f0 dd fc 1c"), 0)    == (7777777777, 5)


def test_header_key_enc_str_bytes():
    assert encode_key(u"foo")       == (0x80, SBytes("03 66 6f 6f"))                                # string
    assert encode_key(u"Виагра")    == (0x80, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"))     # string
    assert encode_key(b"foo")       == (0xc0, SBytes("03 66 6f 6f"))                                # bytes

def test_header_key_dec_str_bytes():
    assert decode_key(0x80, SBytes("03 66 6f 6f"),0)                                == (u"foo", 4)
    assert decode_key(0x80, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),0)     == (u"Виагра", 13)
    assert decode_key(0xc0, SBytes("03 66 6f 6f"),0)                                == (b"foo", 4)


def test_header_enc():
    assert encode_header(key=None,   data_type=5,  data_len=5)    == SBytes("05 05")
    assert encode_header(key=5,      data_type=5,  data_len=5)    == SBytes("45 05 05")
    assert encode_header(key=u"foo", data_type=28, data_len=1500) == SBytes("9c 03 66 6f 6f dc 0b")

def test_header_dec():
    assert decode_header(SBytes("05 05"),0)                 == (None, 5, 5, 2)
    assert decode_header(SBytes("45 05 05"),0)              == (5, 5, 5, 3)
    assert decode_header(SBytes("9c 03 66 6f 6f dc 0b"),0)  == (u"foo", 28, 1500, 7)

