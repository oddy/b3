
# -*- coding: UTF-8 -*-

from test_util import SBytes
from item_header import *


def test_header_key_enc_none_int():
    assert encode_key(None)         == (0x00, b"")
    assert encode_key(4)            == (0x40, SBytes("08"))               # py2 int
    assert encode_key(7777777777)   == (0x40, SBytes("e2 e1 bb f9 39"))   # py2 long

def test_header_key_dec_none_int():
    assert decode_key(0x00, b"", 0)                         == (None, 0)
    assert decode_key(0x40, SBytes("08"), 0)                == (4, 1)
    assert decode_key(0x40, SBytes("e2 e1 bb f9 39"), 0)    == (7777777777, 5)


def test_header_key_enc_str_bytes():
    assert encode_key(u"foo")       == (0x80, SBytes("03 66 6f 6f"))                                # string
    assert encode_key(u"Виагра")    == (0x80, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"))     # string
    assert encode_key(b"foo")       == (0xc0, SBytes("03 66 6f 6f"))                                # bytes

def test_header_key_dec_str_bytes():
    assert decode_key(0x80, SBytes("03 66 6f 6f"),0)                                == (u"foo", 4)
    assert decode_key(0x80, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),0)     == (u"Виагра", 13)
    assert decode_key(0xc0, SBytes("03 66 6f 6f"),0)                                == (b"foo", 4)




