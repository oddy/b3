import pytest, copy

from b3.utils import SBytes
from b3.datatypes import *
from b3.composite_schema import schema_pack, schema_unpack
from b3 import composite_schema  # so we can get to strict_mode

# Item header & data structure is
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# --- Test data schema ---
TEST_SCHEMA = ((UVARINT, "number1", 1), (UTF8, "string1", 2), (BOOL, "bool1", 3))

# --- Shared test data - manually-built packed-bytes buffer ---
number1_data = "45"  # encode_uvarint(69)
number1_header = "39 01 01"  # encode_header(UVARINT, key=1, data_len=1)
string1_data = "66 6f 6f"  # encode_utf8(u"foo")
string1_header = "19 02 03"  # encode_header(UTF8, key=2, data_len=3)
bool1_header = "2D 03"  # encode_item(key=3, data_type=BOOL(2), value=True)

test1_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header])
test1_buf = SBytes(test1_hex)

# --- Shared test data - actual test data to pack ---
test1 = dict(bool1=True, number1=69)
# add string1 at the end to try and influence dict ordering. Order-preserving dicts will have string1
# last, thus bool1 successfully being at the end of pack-generated buffers means the key_number ordering
# is working.
test1["string1"] = u"foo"

# --- Test ignoring additional schema info fields after the first 3 ---
TEST_SCHEMA4 = ((UVARINT, "number1", 1, True), (UTF8, "string1", 2, False), (BOOL, "bool1", 3, True))

# --- Pack/Encoder tests ---

def test_schema_pack_nominal_data():  # "Happy path"
    out1_buf = schema_pack(TEST_SCHEMA, test1)
    assert out1_buf == test1_buf


def test_schema_pack_dictcheck():
    with pytest.raises(TypeError):
        schema_pack(TEST_SCHEMA, [])


def test_schema_pack_ignores_4fields():
    out1_buf = schema_pack(TEST_SCHEMA4, test1)
    assert out1_buf == test1_buf


# --- Field found in input dict which does not exist in schema. Default=ignore it, strict=raise exception. ---


def test_schema_pack_field_unwanted_ignore():
    test2 = copy.copy(test1)
    test2["unwanted_field"] = u"hello"
    composite_schema.strict_mode = False
    buf = schema_pack(TEST_SCHEMA, test2)  # aka strict=False
    assert buf == test1_buf  # ensure unwanted field is not in result data.


def test_schema_pack_field_unwanted_strict():
    test2 = copy.copy(test1)
    test2["unwanted_field"] = u"hello"
    with pytest.raises(KeyError):
        composite_schema.strict_mode = True
        schema_pack(TEST_SCHEMA, test2)


# --- Field exists in shcmea, but missing from input dict, output present with null/None value. ---


def test_schema_pack_field_missing():
    # Testing this buffer...
    bool1_header_null_value = "25 03"  # encode_header(BOOL, key=3, is_null=True)
    bool1_nulled_hex = " ".join(
        [
            number1_header,
            number1_data,
            string1_header,
            string1_data,
            bool1_header_null_value,
        ]
    )
    bool1_nulled_buf = SBytes(bool1_nulled_hex)

    # ...against this data
    test2 = copy.copy(test1)
    del test2["bool1"]
    # ^^ Missing field should be sent out as present but with a null value.

    buf = schema_pack(TEST_SCHEMA, test2)
    assert buf == bool1_nulled_buf


# Note: in py3, if you have a u keyname in the schema and a b keyname in the input dict,
#       schema lookup will FAIL on that keyname, and the outgoing-field-is-missing-make-it-None
#       thing will kick in and your field data wont get sent.
#       - this is why people should dev with strict ON, then (maybe) turn it off later.
#       - we're not going to try and be more helpful here because we could have to pick
#         an encoding etc to compare the strings. Too much pain.

# --- Zero-value compactness check ---


def test_schema_pack_zeroval():
    # Testing this buffer...
    number1_zero_header = "31 01"
    string1_zero_header = "11 02"
    bool1_zero_header = "29 03"
    buf_zv_hex = " ".join([number1_zero_header, string1_zero_header, bool1_zero_header])
    buf_zv = SBytes(buf_zv_hex)

    # ...against this data
    test_zv_data = dict(bool1=False, number1=0, string1="")

    buf = schema_pack(TEST_SCHEMA, test_zv_data)
    assert buf_zv == buf


# --- Nesting UX Test ---
OUTER_SCHEMA = ((BYTES, "bytes1", 1), (SVARINT, "signed1", 2), (DICT, "inner1", 3))


def test_schema_pack_nesting():
    # Testing this buffer...
    bytes1_hex = "09 01 0a 6f 75 74 65 72 62 79 74 65 73"  # header + 'outerbytes'
    signed1_hex = "49 02 02 a3 13"  # header + encode_svarint(-1234)
    # header + buffer output from the zeroval test
    inner_buf_hex = "e9 03 06 31 01 11 02 29 03"

    test_outer_buf = SBytes(" ".join([bytes1_hex, signed1_hex, inner_buf_hex]))

    # ...against this data
    inner_data = dict(bool1=False, number1=0, string1="")
    inner1 = schema_pack(TEST_SCHEMA, inner_data)
    outer_data = dict(bytes1=b"outerbytes", signed1=-1234, inner1=inner1)
    outer_buf = schema_pack(OUTER_SCHEMA, outer_data)

    assert outer_buf == test_outer_buf


# --- Unpack/Decoder tests ---


def test_schema_unpack_nominal_data():  # "Happy path"
    out1_data = schema_unpack(TEST_SCHEMA, test1_buf, 0, len(test1_buf))
    assert out1_data == test1

def test_schema_unpack_nominal_data_4fields():  # "Happy path"
    out1_data = schema_unpack(TEST_SCHEMA4, test1_buf, 0, len(test1_buf))
    assert out1_data == test1


def test_schema_unpack_dictcheck():
    out1_data = schema_unpack(TEST_SCHEMA, test1_buf, 0, len(test1_buf))
    assert isinstance(out1_data, dict)


def test_schema_unpack_unwanted_incoming_field():
    bool2_buf = SBytes("59 04 01 01")  # a second BOOL with key=4, len=1, value=True
    unwantfield_buf = test1_buf + bool2_buf
    out2_data = schema_unpack(TEST_SCHEMA, unwantfield_buf, 0, len(unwantfield_buf))
    # we are asserting that the unwanted field is ignored
    assert out2_data == test1


# It's actually hard to get this to fail. We can feed it a lot of buffer contents, and because
# * Missing fields on the wire are added to the output with None values anyway,
# * Other fields on the wire (not specified by the schema) are ignored,
# unpack will actually yield the desired result quite often.
# Note: the first null_buf value shows what the test data actually looks like when encoded.
def test_schema_unpack_null_data():
    for null_buf in (SBytes("35 01 15 02 25 03"), b""):
        null_data = dict(bool1=None, number1=None, string1=None)
        assert schema_unpack(TEST_SCHEMA, null_buf, 0, len(null_buf)) == null_data


def test_schema_unpack_zero_data():
    zero_buf = SBytes("31 01 11 02 21 03")
    zero_data = dict(bool1=False, number1=0, string1="")
    assert schema_unpack(TEST_SCHEMA, zero_buf, 0, len(zero_buf)) == zero_data


def test_schema_unpack_type_mismatch():
    with pytest.raises(TypeError):
        mismatch_buf = SBytes("31 01   b1 02   21 03")
        # ^^ field 2 is a bytes here (x10) when it should be a utf8 (x11)
        x = schema_unpack(TEST_SCHEMA, mismatch_buf, 0, len(mismatch_buf))


def test_schema_unpack_bytes_yield():
    BYTES_SCHEMA = ((BYTES, "bytes1", 1), (LIST, "list1", 2))
    bytes1_hex = "09 01 03 66 6f 6f"  # b"foo"
    list1_hex = "d9 02 03 66 6f 6f"
    test_buf = SBytes(" ".join([bytes1_hex, list1_hex]))

    test_data = dict(bytes1=b"foo", list1=b"foo")
    assert schema_unpack(BYTES_SCHEMA, test_buf, 0, len(test_buf)) == test_data


def test_schema_unpack_missing_incoming_field():
    missing_fields_buf = SBytes("57 01")  # so only field 1 is present (and null)
    null_data = dict(bool1=None, number1=None, string1=None)
    # ^^^  missing incoming fields should get created and null-valued.
    assert schema_unpack(TEST_SCHEMA, missing_fields_buf, 0, len(missing_fields_buf)) == null_data


# Policy: its expected that the user would save a copy of incoming messages for cases where there are more fields than there are in the schema.


def test_schema_unpack_nesting():
    # Testing this buffer...
    bytes1_hex = "09 01 0a 6f 75 74 65 72 62 79 74 65 73"  # header + 'outerbytes'
    signed1_hex = "49 02 02 a3 13"  # header + encode_svarint(-1234)
    inner_buf_hex = "e9 03 06 31 01 11 02 29 03"  # header + buffer output from the zeroval test
    test_outer_buf = SBytes(" ".join([bytes1_hex, signed1_hex, inner_buf_hex]))

    # Note: It's up to the user to know - presumably using the defined schemas, that inner1 is a
    # Note: DICT type, as the returned dict (outer_data) just has the encoded bytes in that field.
    outer_data = schema_unpack(OUTER_SCHEMA, test_outer_buf, 0, len(test_outer_buf))
    inner_len = len(outer_data["inner1"])
    inner_data = schema_unpack(TEST_SCHEMA, outer_data["inner1"], 0, inner_len)

    assert inner_data == dict(bool1=False, number1=0, string1="")


def test_schema_nested_errors():
    # Nested containers e.g. dict1 and list1 need to be explicitely packed to bytes first.
    # schema_pack should raise an error if it sees un-packed python dicts or lists in the fields.
    NEST_SCHEMA = (
        (DICT, "dict1", 1),
        (LIST, "list1", 2),
    )

    data = dict(dict1={1: 2, 3: 4}, list1=[7, 8, 9])

    with pytest.raises(TypeError):
        schema_pack(NEST_SCHEMA, data)


# --- Roundtrip / all data types testing ---


def test_schema_alltypes_roundtrip():
    from decimal import Decimal
    from datetime import datetime

    ALLTYPES_SCHEMA = (
        (BYTES, "bytes1", 1),
        (UTF8, "string1", 2),
        (BOOL, "bool1", 3),
        (UVARINT, "uvint1", 4),
        (SVARINT, "svint1", 5),
        (U64, "u641", 6),
        (S64, "s641", 7),
        (FLOAT64, "float1", 8),
        (DECIMAL, "deci1", 9),
        (SCHED, "date1", 10),
        (COMPLEX, "cplx1", 11),
    )

    data = dict(
        bytes1=b"foo",
        string1=u"bar",
        bool1=True,
        uvint1=456,
        svint1=-789,
        u641=123,
        s641=123,
        float1=13.37,
        deci1=Decimal("13.37"),
        date1=datetime.now(),
        cplx1=33j,
    )

    buf = schema_pack(ALLTYPES_SCHEMA, data)

    out = schema_unpack(ALLTYPES_SCHEMA, buf, 0, len(buf))

    assert data == out


# Policy: schema type and message type are only checked for match if the value isn't None/NULL/Nil (None is its own type)
#         this is favouring interop (with Dynamic, who can't type-set Nones) over correctness.
#         Call unpack with strict=True to favour correctness and always check, even with nulls.

# Strict defaults to false, nulls bypass the strict type-check.
def test_schema_unpack_type_mismatch_nulls():
    mismatch_buf = SBytes("31 01   85 02   21 03")
    # ^^ field 2 is coming in as a decimal here when it should be a utf8
    composite_schema.strict_mode = False
    x = schema_unpack(TEST_SCHEMA, mismatch_buf, 0, len(mismatch_buf))
    assert True  # as in it didn't blow up with an exception, which is what we want.


# Set strict=True to cause a TypeError if there is a type mismatch, regardless of null values.
def test_schema_unpack_type_mismatch_nulls_strict():
    with pytest.raises(TypeError):
        mismatch_buf = SBytes("31 01   85 02   21 03")
        # ^^ field 2 is coming in as a decimal here when it should be a utf8
        composite_schema.strict_mode = True
        x = schema_unpack(TEST_SCHEMA, mismatch_buf, 0, len(mismatch_buf))


# --- possibly for the nesting example? ---
# from b3 import pack
# data['dict1'] = pack(data['dict1'], with_header=False)
# data['list1'] = pack(data['list1'], with_header=False)
#
# buf = schema_pack(ALLTYPES_SCHEMA, data)
# out = schema_unpack(ALLTYPES_SCHEMA, buf, 0, len(buf))
#
# from pprint import pprint
# print("Data:")
# pprint(data)
# print("Out:")
# pprint(out)
#
# assert out == data

# def test_schema_unpack_interop():
#     buf_from_pack = 'A)t\x07string1\x0bhello worldu\x05bool1\x01\x01w\x07number1\x01x'    # see test_comp_dynamic
#     buf = buf_from_pack[2:]     # strip pack's outer-header.
#     from pprint import pprint
#     pprint(schema_unpack(TEST_SCHEMA, buf, 0, len(buf)))

# ==========
# = unpack_into can unpack the buffer output from test_schema_pack_nesting() !

# >>> from b3 import unpack
# >>> from b3.utils import SBytes
# >>> j = "93 01 0a 6f 75 74 65 72 62 79 74 65 73 98 02 02 a3 13 51 03 06 17 01 14 02 15 03"     # <-- output from above
# >>> k = SBytes(j)
# >>> k
# 'S\x01\nouterbytesX\x02\x02\xa3\x13Q\x03\x06\x17\x01\x14\x02\x15\x03'

# >>> unpack(k, 0, len(k))
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "b3\composite_dynamic.py", line 85, in unpack
#     raise TypeError("Expecting list or dict container type first in message, but got %i" % (data_type,))
# TypeError: Expecting list or dict container type first in message, but got 3

# >>> from b3.composite_dynamic import unpack_into
# >>> out = {}
# >>> unpack_into(out, k, 0, len(k))
# >>> out

# {1: 'outerbytes', 2: -1234, 3: {1: 0, 2: u'', 3: False}}
