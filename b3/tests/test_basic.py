# -*- coding: UTF-8 -*-
import pytest

from b3.utils import SBytes
from b3.type_basic import *
from b3.item import (
    encode_item,
    decode_header,
    decode_item,
    encode_item_joined,
    decode_item_type_value,
)
from b3.datatypes import *

# Note: these above break with ImportError No module named b3, UNLESS i make the tests a package by adding an empty __init__.py
# Note: once i do that, then everything seems to work perfectly. I think this is pytest magic, not sure.


# The bool 'codec' is special, lives in the item header, reuses the null/zero flag to transport it's value.

TEST_DECODE_BOOLS = (
    (SBytes("24"), None),  # null
    (SBytes("20"), False),  # normal compact-zero-value case
    (SBytes("28"), False),  # bool bit 0
    (SBytes("2C"), True),  # bool bit 1
)


@pytest.mark.parametrize("tbytes,tvalue", TEST_DECODE_BOOLS)
def test_bool_decode(tbytes, tvalue):
    _, val, _ = decode_item(tbytes, 0)
    assert val == tvalue


TEST_ENCODE_BOOLS = ((None, SBytes("24")), (False, SBytes("28")), (True, SBytes("2C")))


@pytest.mark.parametrize("tvalue,tbytes", TEST_ENCODE_BOOLS)
def test_bool_encode(tvalue, tbytes):
    hdr_bytes, val_bytes = encode_item(key=None, data_type=B3_BOOL, value=tvalue)
    assert val_bytes == b""
    assert hdr_bytes == tbytes


# --------------------------------------------------------------------------------------------------

# BMP 0000-FFFF,  SMP 10000-1FFFF,  SIP 20000-2FFFF,  TIP 30000-3FFFF
# Went and got the utf8 bytes from the equivalent golang script
TEST_UNISTRS = (
    ("hello world", SBytes("68 65 6c 6c 6f 20 77 6f 72 6c 64")),
    ("Виагра", SBytes("d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0")),  # Viagra OWEN
    ("✈✉🚀🚸🚼🚽", SBytes("e2 9c 88 e2 9c 89 f0 9f 9a 80 f0 9f 9a b8 f0 9f 9a bc f0 9f 9a bd")),  # SMP
    ("", b""),  # zero-length strings
)


def test_base_utf8_enc():
    for tstr, tbytes in TEST_UNISTRS:
        assert encode_utf8(tstr) == tbytes


def test_base_utf8_dec():
    for tstr, tbytes in TEST_UNISTRS:
        assert decode_utf8(tbytes, 0, len(tbytes)) == tstr


# --------------------------------------------------------------------------------------------------

# FTR float32 is trash and we shouldn't really be using == to test it. 12345.5 round-tripping
# successfully is just a lucky break, 12345.6 doesn't. Its used a "lot in gaming and ML" tho apparently.

TEST_NUM_VALUES = (
    ("u32", B3_U32, 123456789,  SBytes("58 04 15 cd 5b 07")),
    ("s32", B3_S32, -123456789, SBytes("68 04 eb 32 a4 f8")),
    ("u64", B3_U64, 123456789,  SBytes("78 08 15 cd 5b 07 00 00 00 00")),
    ("s64", B3_S64, -123456789, SBytes("88 08 eb 32 a4 f8 ff ff ff ff")),
    ("f32", B3_FLOAT32, 12345.5, SBytes("98 04 00 e6 40 46")),
    ("f64", B3_FLOAT64, 12345.6789, SBytes("a8 08 a1 f8 31 e6 d6 1c c8 40")),
    ("u32_0", B3_U32, 0, SBytes("50")),
    ("s32_0", B3_S32, 0, SBytes("60")),
    ("u64_0", B3_U64, 0, SBytes("70")),
    ("s64_0", B3_S64, 0, SBytes("80")),
    ("f32_0", B3_FLOAT32, 0.0, SBytes("90")),
    ("f64_0", B3_FLOAT64, 0.0, SBytes("a0")),
)

# u32  "<L"  ("u32", B3_U32, 123456789,  SBytes("58 04 15 cd 5b 07")),
# s32  "<l"  ("s32", B3_S32, -123456789, SBytes("68 04 eb 32 a4 f8")),
# u64  "<Q"  ("u64", B3_U64, 123456789,  SBytes("78 08 15 cd 5b 07 00 00 00 00")),
# s64  "<q"  ("s64", B3_S64, -123456789, SBytes("88 08 eb 32 a4 f8 ff ff ff ff")),
# f32  "<f"  ("f32", B3_FLOAT32, 12345.6789, SBytes("98 04 b7 xe 36 40 46")),
# f64  "<d"  ("f64", B3_FLOAT64, 12345.6789, SBytes("a8 08 a1 f8 31 e6 d6 1c c8 40")),

@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_NUM_VALUES)
def test_number_encode(desc, ttype, tvalue, tbytes):
    assert encode_item_joined(key=None, data_type=ttype, value=tvalue) == tbytes


@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_NUM_VALUES)
def test_number_decode(desc, ttype, tvalue, tbytes):
    data_type, value = decode_item_type_value(tbytes)
    assert data_type == ttype
    assert value == tvalue




# --------------------------------------------------------------------------------------------------


tcplx = 13.37 + 42.42j
tcplx_bytes = SBytes("3d 0a d7 a3 70 bd 2a 40 f6 28 5c 8f c2 35 45 40")


def test_base_complex_enc():
    assert encode_complex(tcplx) == tcplx_bytes
    assert encode_complex(0j) == SBytes("")


def test_base_complex_dec():
    assert decode_complex(tcplx_bytes, 0, 16) == tcplx
    assert decode_complex(SBytes(""), 0, 0) == 0j
    assert decode_complex(SBytes("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"), 0, 16) == 0j
