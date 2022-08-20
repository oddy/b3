# -*- coding: UTF-8 -*-

from b3.utils import SBytes
from b3.item import *

# Note: encode_item takes (key, data_type, value)
# Note: decode_header returns    (key, data_type, has_data, is_null, data_len, index)

# --- Kitchen sink ---
def test_enc_header_all():
    assert encode_item(key=u"foo", data_type=555, value=b"\xbe\xef") == (
        SBytes("fa ab 04 03 66 6f 6f 02"),
        SBytes("be ef"),
    )
    #           --                              control: data_type=extended(f) data=yes null=no key=1,0 (UTF8)
    #              -----                        ext type uvarint (555)
    #                    --                     len of utf8 key (3 bytes)
    #                       --------            utf8 key u"foo"
    #                                --         data len (2)


def test_dec_header_all():
    hbytes = SBytes("fa ab 04 03 66 6f 6f dc 0b")
    assert decode_header(hbytes, 0) == (u"foo", 555, True, False, 1500, 9)


# --- key types ---


def test_enc_keytype_none_int():
    assert encode_key(None) == (0x00, b"")
    assert encode_key(4) == (0x01, SBytes("04"))  # py2 int
    assert encode_key(7777777777) == (0x01, SBytes("f1 f0 dd fc 1c"))  # py2 long


def test_dec_keytype_none_int():
    assert decode_key(0x00, b"", 0) == (None, 0)
    assert decode_key(0x01, SBytes("04"), 0) == (4, 1)
    assert decode_key(0x01, SBytes("f1 f0 dd fc 1c"), 0) == (7777777777, 5)


def test_enc_keytype_str_bytes():
    assert encode_key(u"foo") == (0x02, SBytes("03 66 6f 6f"))  # string key
    assert encode_key(u"Виагра") == (
        0x02,
        SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),
    )
    assert encode_key(b"foo") == (0x03, SBytes("03 66 6f 6f"))  # bytes key


def test_dec_keytype_str_bytes():
    assert decode_key(0x02, SBytes("03 66 6f 6f"), 0) == (u"foo", 4)
    assert decode_key(0x02, SBytes("0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"), 0) == (
        u"Виагра",
        13,
    )
    assert decode_key(0x03, SBytes("03 66 6f 6f"), 0) == (b"foo", 4)


# Note: encode_item takes (key, data_type, value)

# --- Header null & has-data bits ENcoder ---

# null, no data
def test_enc_header_null():
    assert encode_item(None, 0, None) == (SBytes("04"), b"")


# has-data on, size follows
def test_enc_header_hasdata():
    assert encode_item(None, 0, b"\xbe\xef") == (SBytes("08 02"), SBytes("be ef"))


# no data but not null = compact zero-value mode
def test_enc_header_zeroval():
    assert encode_item(None, 0, b"") == (SBytes("00"), b"")


def test_enc_header_datalen():
    assert encode_item(None, 0, b"A" * 5) == (SBytes("08 05"), b"A" * 5)
    assert encode_item(None, 0, b"A" * 1500) == (SBytes("08 dc 0b"), b"A" * 1500)


# --- Header null & has-data bits DEcoder ---

# Note: decode_header returns    (key, data_type, has_data, is_null, data_len, index)

# is_null True
def test_dec_header_null():
    assert decode_header(SBytes("04"), 0) == (None, 0, False, True, 0, 1)


# with length byte value 5
def test_dec_header_hasdata_1():
    assert decode_header(SBytes("08 05"), 0) == (None, 0, True, False, 5, 2)


# with length byte value 144
def test_dec_header_hasdata_2():
    assert decode_header(SBytes("08 90 01"), 0) == (None, 0, True, False, 144, 3)


# not null, not has-data, so zero-value
def test_dec_header_zeroval():
    assert decode_header(SBytes("00"), 0) == (None, 0, False, False, 0, 1)


# shows it is ignoring the subsequent byte(s)
# Note this will cause problems for subsequent processing, but thats up to the user code to sort out.
def test_dec_header_zeroval_2():
    assert decode_header(SBytes("00 ee"), 0) == (None, 0, False, False, 0, 1)


# Note: decode_header returns    (key, data_type, has_data, is_null, data_len, index)
#       encode item takes (key, data_type, value)

# --- Ext data type numbers ---

# Using the None/Null path through encode_item, so we can test just the data_type numbers
def test_enc_header_exttype():
    assert encode_item(None, 5, None) == (SBytes("54"), b"")
    assert encode_item(None, 14, None) == (SBytes("e4"), b"")
    assert encode_item(None, 15, None) == (SBytes("f4 0f"), b"")
    assert encode_item(None, 16, None) == (SBytes("f4 10"), b"")
    assert encode_item(None, 555, None) == (SBytes("f4 ab 04"), b"")


def test_dec_header_exttype():
    assert decode_header(SBytes("54"), 0) == (None, 5, False, True, 0, 1)
    assert decode_header(SBytes("e4"), 0) == (None, 14, False, True, 0, 1)
    assert decode_header(SBytes("f4 0f"), 0) == (None, 15, False, True, 0, 2)
    assert decode_header(SBytes("f4 10"), 0) == (None, 16, False, True, 0, 2)
    assert decode_header(SBytes("f4 ab 04"), 0) == (None, 555, False, True, 0, 3)


# Note: decode_header returns     (key, data_type, has_data, is_null, data_len, index)

# --- Keys ---

# Using bytes data_type and zero value for bytes (b"") so we can test just the keys


def test_enc_header_keys():
    assert encode_item(None, 0, b"") == (SBytes("00"), b"")
    assert encode_item(4, 0, b"") == (SBytes("01 04"), b"")
    assert encode_item(7777777777, 0, b"") == (SBytes("01 f1 f0 dd fc 1c"), b"")
    assert encode_item(u"foo", 0, b"") == (SBytes("02 03 66 6f 6f"), b"")
    assert encode_item(u"Виагра", 0, b"") == (
        SBytes("02 0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"),
        b"",
    )
    assert encode_item(b"foo", 0, b"") == (SBytes("03 03 66 6f 6f"), b"")


def test_dec_header_keys():
    assert decode_header(SBytes("00"), 0) == (None, 0, False, False, 0, 1)
    assert decode_header(SBytes("01 04"), 0) == (4, 0, False, False, 0, 2)
    assert decode_header(SBytes("01 f1 f0 dd fc 1c"), 0) == (
        7777777777,
        0,
        False,
        False,
        0,
        6,
    )
    assert decode_header(SBytes("02 03 66 6f 6f"), 0) == ("foo", 0, False, False, 0, 5)
    assert decode_header(SBytes("02 0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0"), 0) == (
        u"Виагра",
        0,
        False,
        False,
        0,
        14,
    )
    assert decode_header(SBytes("03 03 66 6f 6f"), 0) == (b"foo", 0, False, False, 0, 5)
