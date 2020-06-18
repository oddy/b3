
# -*- coding: UTF-8 -*-

from .utils import SBytes
from .item_header import *

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | is null    | has data   | key type   | key type   | data type  | data type  | data type  | data type  |
# +------------+------------+------------+------------+------------+------------+------------+------------+


# --- Header key types ---

def test_keytype_none_int_enc():
    assert encode_key(None)         == (0x00, b"")
    assert encode_key(4)            == (0x10, SBytes("04"))               # py2 int
    assert encode_key(7777777777)   == (0x10, SBytes("f1 f0 dd fc 1c"))   # py2 long


def test_keytype_none_int_dec():
    assert decode_key(0x00, b"", 0)                         == (None, 0)
    assert decode_key(0x10, SBytes("04"), 0)                == (4, 1)
    assert decode_key(0x10, SBytes("f1 f0 dd fc 1c"), 0)    == (7777777777, 5)


def test_keytype_enc_str_bytes():
    assert encode_key(u"foo")       == (0x20, SBytes("03 66 6f 6f"))                                # string
    assert encode_key(u"Виагра")    == (0x20, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"))     # string key
    assert encode_key(b"foo")       == (0x30, SBytes("03 66 6f 6f"))                                # bytes key

def test_keytype_dec_str_bytes():
    assert decode_key(0x20, SBytes("03 66 6f 6f"),0)                                == (u"foo", 4)
    assert decode_key(0x20, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),0)     == (u"Виагра", 13)
    assert decode_key(0x30, SBytes("03 66 6f 6f"),0)                                == (b"foo", 4)


# --- Header null & has-data bits ENcoder ---

def test_header_null_enc():
    assert encode_header(key=None, data_type=0,  data_len=0, is_null=True)   == SBytes("80")        # null bit on

# ensure null supercedes any datalen info
# this is not a valid state. We want to ensure that null clobbers the datalen stuff if it's on.
# with null ON, has-data should be OFF in spite of supplied data_len 1!
def test_header_hasdata_and_null():
    assert encode_header(key=None, data_type=0,  data_len=5, is_null=True)   == SBytes("80")        # null bit on. has-data OFF, no size.

def test_header_hasdata_enc():
    assert encode_header(key=None, data_type=0,  data_len=5, is_null=False)  == SBytes("40 05")     # has-data on, size follows

def test_header_zeroval_enc():
    assert encode_header(key=None, data_type=0,  data_len=0, is_null=False)  == SBytes("00")        # not null but no data = zero-value mode



# --- Header null & has-data bits DEcoder ---

# decode_header returns                            (key, data_type, is_null, data_len, index)

def test_header_null_dec():
    assert decode_header(SBytes("80"),0)        == (None, 0, True, 0, 1)               # is_null True

# has-data should never be on if is-null is on. is-null forces has-data off and stops datalen processing.

def test_header_null_hasdata_dec():
    assert decode_header(SBytes("c0"),0)        == (None, 0, True, 0, 1)               # is_null True, data_len 0

def test_header_hasdata_dec():
    assert decode_header(SBytes("40 05"),0)     == (None, 0, False, 5, 2)           # with length byte value 5
    assert decode_header(SBytes("40 90 01"),0)  == (None, 0, False, 144, 3)         # with length byte value 144

def test_header_zeroval_dec():
    assert decode_header(SBytes("00"),0)        == (None, 0, False, 0, 1)           # not null, not has-data
    assert decode_header(SBytes("00 ee"),0)     == (None, 0, False, 0, 1)           # shows it is ignoring the subsequent byte(s)







#
#
# def test_header_keytype_enc():
#     assert encode_header(key=None,   data_type=5,  data_len=5)    == SBytes("45 05")
#
# def test_header_datalen_enc():
#     assert encode_header(key=None,   data_type=5,  data_len=5)    == SBytes("45 05")
#     assert encode_header(key=5,      data_type=5,  data_len=5)    == SBytes("55 05 05")
#
#     #assert encode_header(key=u"foo", data_type=28, data_len=1500) == SBytes("6c 03 66 6f 6f dc 0b")
#
# def test_header_enc_null():
#     assert encode_header(key=None,   data_type=5,  data_len=0, is_null=True)  == SBytes("25")       # note no size
#
# def test_header_datalen_dec():
#     assert decode_header(SBytes("05 05"),0)                 == (None, 5, False, 5, 2)
#     assert decode_header(SBytes("45 05 05"),0)              == (5, 5, False, 5, 3)
#     assert decode_header(SBytes("9c 03 66 6f 6f dc 0b"),0)  == (u"foo", 28, False, 1500, 7)
#
# def test_header_dec_null():
#     assert decode_header(SBytes("25"),0) == (None, 5, True, 0, 1)       # note no size
#
