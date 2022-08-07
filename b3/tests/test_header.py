
# -*- coding: UTF-8 -*-

import pytest

from b3.utils import SBytes
from b3.item_header import *

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | has data   | null/zero  | key type   | key type   | data type  | data type  | data type  | data type  |
# +------------+------------+------------+------------+------------+------------+------------+------------+

# --- Control flags ---
# +------------+------------+
# | has data   | null/zero  |
# +------------+------------+
#     0   0  (0)    Codec zero-value for given data type (0, "", 0.0 etc)
#     0   1  (1)    None/NULL/nil
#     1   x  (2)    Data len present, data bytes present, null/zero flag unused.


# --- Key types ---
# +------------+------------+
# | key type   | key type   |
# +------------+------------+
#     0   0  (0)    no key
#     0   1  (4)    UVARINT
#     1   0  (8)    UTF8 bytes
#     1   1  (c)    raw bytess


# --- key types ---

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
    assert encode_header(data_type=0,  data_len=0, is_null=True)   == SBytes("40")        # null bit on

def test_header_hasdata_enc():
    assert encode_header(data_type=0,  data_len=5, is_null=False)  == SBytes("80 05")     # has-data on, size follows

def test_header_zeroval_enc():
    assert encode_header(data_type=0,  data_len=0, is_null=False)  == SBytes("00")        # not null but no data = compact zero-value mode

# ENCODER:
# API Policy: is_null supercedes any datalen info. If null is on, data_len forced to 0, has_data forced to false.

def test_header_hasdata_but_null_enc():
    assert encode_header(data_type=0,  data_len=5, is_null=True)   == SBytes("40")        # null bit on. has-data OFF, no size.


# --- Header null & has-data bits DEcoder ---

# Note: decode_header returns                      (data_type, key, is_null, data_len, index)

def test_header_null_dec():
    assert decode_header(SBytes("40"), 0)        == (0, None, True, 0, 1)            # is_null True

# Policy: DEcoder: if has_data is true then ignore null/zero (but return its value)
#         (We eventually may use the null/zero as a user-flag when there's data, but its ignored for now.

def test_header_hasdata_dec():
    assert decode_header(SBytes("80 05"),0)     == (0, None, False, 5, 2)           # with length byte value 5
    assert decode_header(SBytes("80 90 01"),0)  == (0, None, False, 144, 3)         # with length byte value 144

def test_header_zeroval_dec():
    assert decode_header(SBytes("00"),0)        == (0, None, False, 0, 1)           # not null, not has-data
    assert decode_header(SBytes("00 ee"),0)     == (0, None, False, 0, 1)           # shows it is ignoring the subsequent byte(s)


# --- Data len ---

def test_header_datalen_enc():
    assert encode_header(data_type=5, data_len=5)    == SBytes("85 05")
    assert encode_header(data_type=5, data_len=1500) == SBytes("85 dc 0b")

def test_header_datalen_dec():
    assert decode_header(SBytes("85 05"),0)     == (5, None,  False, 5, 2)
    assert decode_header(SBytes("85 dc 0b"),0)  == (5, None,  False, 1500, 3)


# Note: decode_header returns                      (data_type, key, is_null, data_len, index)

# --- Ext data type numbers ---

def test_header_exttype_enc():
    assert encode_header(data_type=5)    == SBytes("05")
    assert encode_header(data_type=14)   == SBytes("0e")
    assert encode_header(data_type=15)   == SBytes("0f 0f")
    assert encode_header(data_type=16)   == SBytes("0f 10")
    assert encode_header(data_type=555)  == SBytes("0f ab 04")

def test_header_exttype_dec():
    assert decode_header(SBytes("05"),0)        == (5,  None,  False, 0, 1)
    assert decode_header(SBytes("0e"),0)        == (14, None,  False, 0, 1)
    assert decode_header(SBytes("0f 0f"),0)     == (15, None,  False, 0, 2)
    assert decode_header(SBytes("0f 10"),0)     == (16, None,  False, 0, 2)
    assert decode_header(SBytes("0f ab 04"),0)  == (555, None, False, 0, 3)


# --- Keys ---

def test_header_keys_enc():
    assert encode_header(0, key=None)           == SBytes("00")
    assert encode_header(0, key=4)              == SBytes("10 04")
    assert encode_header(0, key=7777777777)     == SBytes("10 f1 f0 dd fc 1c")
    assert encode_header(0, key=u"foo")         == SBytes("20 03 66 6f 6f")
    assert encode_header(0, key=u"Виагра")      == SBytes("20 0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0")
    assert encode_header(0, key=b"foo")         == SBytes("30 03 66 6f 6f")

def test_header_keys_dec():
    assert decode_header(SBytes("00"),0)                    == (0, None,       False, 0, 1)
    assert decode_header(SBytes("10 04"),0)                 == (0, 4,          False, 0, 2)
    assert decode_header(SBytes("10 f1 f0 dd fc 1c"),0)     == (0, 7777777777, False, 0, 6)
    assert decode_header(SBytes("20 03 66 6f 6f"),0)        == (0, u"foo",     False, 0, 5)
    assert decode_header(SBytes("20 0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),0)  == (0, u"Виагра", False, 0, 14)
    assert decode_header(SBytes("30 03 66 6f 6f"),0)        == (0, b"foo",     False, 0, 5)


# --- Kitchen-sink ---

def test_header_all_enc():
    assert encode_header(data_type=555, key=u"foo", data_len=1500, is_null=False) == \
        SBytes("af ab 04 03 66 6f 6f dc 0b")
        #       --                              control: data=yes null=no key=1,0 (UTF8)  data_type=extended (1,1,1,1)
        #          -----                        ext type uvarint (555)
        #                --                     len of utf8 key (3 bytes)
        #                   --------            utf8 key u"foo"
        #                            -----      data len (1500)

def test_header_all_2_enc():
    assert encode_header(data_type=7, key=b"\x01\x02\x03", data_len=6, is_null=False) == \
        SBytes("b7 03 01 02 03 06")

# Note: decode_header returns                                       (data_type, key, is_null, data_len, index)

def test_header_all_dec():
    assert decode_header(SBytes("af ab 04 03 66 6f 6f dc 0b"),0) == (555, u"foo", False, 1500, 9)

