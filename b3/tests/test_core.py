# -*- coding: UTF-8 -*-
import datetime, decimal
import pytest

from b3.utils import SBytes
from b3.item import encode_item, decode_item, encode_item_joined, decode_item_type_value
from b3.datatypes import *

# Note: encode_item takes    (key, data_type, value)
# Note: decode_header returns    (key, data_type, has_data, is_null, data_len, index)

# --------------------------------------------------------------------------------------------------
def test_enc_bytes():
    assert encode_item_joined(None, BYTES, b"\xbe\xef") == SBytes("08 02 be ef")


def test_enc_bytes_z():
    assert encode_item_joined(None, BYTES, b"") == SBytes("00")


def test_dec_bytes():
    assert decode_item_type_value(SBytes("08 02 be ef")) == (BYTES, b"\xbe\xef")


def test_dec_bytes_z():
    assert decode_item_type_value(SBytes("00")) == (BYTES, b"")


# --------------------------------------------------------------------------------------------------

# BMP 0000-FFFF,  SMP 10000-1FFFF,  SIP 20000-2FFFF,  TIP 30000-3FFFF
# Went and got the utf8 bytes from the equivalent golang script
TEST_UNISTRS = (
    (u"hello world", SBytes("18 0b 68 65 6c 6c 6f 20 77 6f 72 6c 64")),
    (u"Виагра", SBytes("18 0c d0 92 d0 b8 d0 b0 d0 b3 d1 80 d0 b0")),  # Viagra OWEN
    (
        u"✈✉🚀🚸🚼🚽",
        SBytes("18 16 e2 9c 88 e2 9c 89 f0 9f 9a 80 f0 9f 9a b8 f0 9f 9a bc f0 9f 9a bd"),
    ),
    (u"", SBytes("10")),  # only the header, no data
)


@pytest.mark.parametrize("tstr,tbytes", TEST_UNISTRS)
def test_enc_utf8(tstr, tbytes):
    assert encode_item_joined(None, UTF8, tstr) == tbytes


@pytest.mark.parametrize("tstr,tbytes", TEST_UNISTRS)
def test_dec_utf8(tstr, tbytes):
    assert decode_item_type_value(tbytes) == (UTF8, tstr)


# --------------------------------------------------------------------------------------------------
# The bool 'codec' is special, lives in the item header, reuses the null/zero flag to transport it's value.

TEST_DECODE_BOOLS = (
    (SBytes("24"), None),  # null
    (SBytes("20"), False),  # normal compact-zero-value case
    (SBytes("28"), False),  # bool bit 0
    (SBytes("2C"), True),  # bool bit 1
)
TEST_ENCODE_BOOLS = ((None, SBytes("24")), (False, SBytes("28")), (True, SBytes("2C")))


@pytest.mark.parametrize("tvalue,tbytes", TEST_ENCODE_BOOLS)
def test_enc_bool(tvalue, tbytes):
    hdr_bytes, val_bytes = encode_item(key=None, data_type=BOOL, value=tvalue)
    assert val_bytes == b""
    assert hdr_bytes == tbytes


@pytest.mark.parametrize("tbytes,tvalue", TEST_DECODE_BOOLS)
def test_dec_bool(tbytes, tvalue):
    _, val, _ = decode_item(tbytes, 0)
    assert val == tvalue


# --------------------------------------------------------------------------------------------------

TEST_NUM_VALUES = (
    ("uvarint_0", UVARINT, 0, SBytes("30")),
    ("svarint_0", SVARINT, 0, SBytes("40")),
    ("u64_0", U64, 0, SBytes("50")),
    ("s64_0", S64, 0, SBytes("60")),
    ("f64_0", FLOAT64, 0.0, SBytes("70")),
    ("complex_0", COMPLEX, 0j, SBytes("f0 10")),
    ("uvarint", UVARINT, 123456789, SBytes("38 04 95 9a ef 3a")),
    ("svarint", SVARINT, -123456789, SBytes("48 04 a9 b4 de 75")),
    ("u64", U64, 123456789, SBytes("58 08 15 cd 5b 07 00 00 00 00")),
    ("s64", S64, -123456789, SBytes("68 08 eb 32 a4 f8 ff ff ff ff")),
    ("f64", FLOAT64, 12345.6789, SBytes("78 08 a1 f8 31 e6 d6 1c c8 40")),
    (
        "complex",
        COMPLEX,
        13.37 + 42.42j,
        SBytes("f8 10 10 3d 0a d7 a3 70 bd 2a 40 f6 28 5c 8f c2 35 45 40"),
    ),
)


@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_NUM_VALUES)
def test_enc_number(desc, ttype, tvalue, tbytes):
    assert encode_item_joined(key=None, data_type=ttype, value=tvalue) == tbytes


@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_NUM_VALUES)
def test_dec_number(desc, ttype, tvalue, tbytes):
    data_type, value = decode_item_type_value(tbytes)
    assert data_type == ttype
    assert value == tvalue


# --------------------------------------------------------------------------------------------------

# Ensure the codec-varint decoder routines correctly deal with a field that's sized wrong
# (ie the field size should match the varint's self-sizing size, error if not.)

def test_dec_uvarint_badsize_lg():
    tbytes = SBytes("38 05 85 a3 a8 6a 10")
    with pytest.raises(ValueError):
        data_type, value = decode_item_type_value(tbytes)

def test_dec_svarint_badsize_lg():
    tbytes = SBytes("48 05 85 a3 a8 6a 10")
    with pytest.raises(ValueError):
        data_type, value = decode_item_type_value(tbytes)

def test_dec_uvarint_badsize_sm():
    tbytes = SBytes("38 03 85 a3 a8 6a 10")
    with pytest.raises(ValueError):
        data_type, value = decode_item_type_value(tbytes)

def test_dec_svarint_badsize_sm():
    tbytes = SBytes("48 03 85 a3 a8 6a 10")
    with pytest.raises(ValueError):
        data_type, value = decode_item_type_value(tbytes)



# --------------------------------------------------------------------------------------------------

# Sched and decimal basic tests (incl zerovalues).
# Codec tests for sched and decimal have their own test file.
# Note passing the value to decimal.Decimal as a string to ensure precision.
# Policy: datetime zerovalue is somewhat arbitrary,
#         but matches golang zero-value time, except for the Aware and UTC parts.

TEST_DECSCHED_VALUES = (
    ("decimal_0", DECIMAL, 0.0, SBytes("80")),
    ("decimal", DECIMAL, decimal.Decimal("12345.6789"), SBytes("88 05 24 95 9a ef 3a")),
    ("sched_0", SCHED, datetime.datetime(1, 1, 1), SBytes("90")),
    (
        "sched",
        SCHED,
        datetime.datetime(2022, 4, 4, 16, 45, 43, 2718),
        SBytes("98 0a c2 cc 1f 04 04 10 2d 2b 9e 15"),
    ),
)


@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_DECSCHED_VALUES)
def test_enc_decsched(desc, ttype, tvalue, tbytes):
    assert encode_item_joined(key=None, data_type=ttype, value=tvalue) == tbytes


@pytest.mark.parametrize("desc,ttype,tvalue,tbytes", TEST_DECSCHED_VALUES)
def test_dec_decsched(desc, ttype, tvalue, tbytes):
    data_type, value = decode_item_type_value(tbytes)
    assert data_type == ttype
    assert value == tvalue
