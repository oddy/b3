
import pytest, copy

from .utils import SBytes
from .datatypes import *
from .composite_schema import schema_pack, schema_unpack, UnwantedFieldError
from .hexdump import hexdump

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- Test data schema ---

TEST_SCHEMA_1 = (
    (B3_UVARINT, "number1", 1),
    (B3_UTF8,    "string1", 2),
    (B3_BOOL,    "bool1",   3)
    )

# --- Test data manually-built packed-bytes buffer ---

number1_data   = "45"                   # encode_uvarint(69)
number1_header = "57 01 01"             # encode_header(B3_UVARINT, key=1, data_len=1)
string1_data   = "66 6f 6f"             # encode_utf8(u"foo")
string1_header = "54 02 03"             # encode_header(B3_UTF8, key=2, data_len=3)
bool1_data     = "01"                   # encode_bool(True)
bool1_header   = "55 03 01"             # encode_header(B3_BOOL, key=3, data_len=1)

test1_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header, bool1_data])
test1_buf = SBytes(test1_hex)

# --- Actual test data to pack ---

test1 = dict(bool1=True, number1=69)
# add string1 at the end to try and influence dict ordering. Order-preserving dicts will have string1
# last, thus bool1 successfully being at the end of pack-generated buffers means the key_number ordering
# is working.
test1["string1"] = u"foo"



# --- Pack/Encoder tests ---

def test_schema_pack_happy():
    out1_buf = schema_pack(TEST_SCHEMA_1, test1)
    # print(u"\n%s\n%s\n" % (hexdump(test1_buf), hexdump(out1_buf)))
    assert out1_buf  == test1_buf

def test_schema_pack_dictcheck():
    with pytest.raises(TypeError):
        schema_pack(TEST_SCHEMA_1, [])

# --- Field found in input dict which does not exist in schema. Default=ignore it, strict=raise exception. ---

def test_schema_pack_field_unwanted_ignore():
    test2 = copy.copy(test1)
    test2['unwanted_field'] = "hello"
    buf = schema_pack(TEST_SCHEMA_1, test2)             # aka strict=False
    assert buf == test1_buf                             # ensure unwanted field is not in result data.

def test_schema_pack_field_unwanted_strict():
    test2 = copy.copy(test1)
    test2['unwanted_field'] = "hello"
    with pytest.raises(UnwantedFieldError):             # Note: catching KeyError also works here.
        schema_pack(TEST_SCHEMA_1, test2, strict=True)

# --- Field missing from input dict but exists in schema, output present with null/None value. ---

def test_schema_pack_field_missing():
    # Testing this buffer...
    bool1_header_null_value   = u"95 03"                # encode_header(B3_BOOL, key=3, is_null=True)
    bool1_nulled_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header_null_value])  # note no data for bool1
    bool1_nulled_buf = SBytes(bool1_nulled_hex)

    # ...against this data
    test2 = copy.copy(test1)
    del test2['bool1']

    buf = schema_pack(TEST_SCHEMA_1, test2)
    assert buf == bool1_nulled_buf

# Note: in py3, if you have a u keyname in the schema and a b keyname in the input dict, schema lookup will fail on that keyname
# and the outgoing-field-is-missing-make-it-None thing will kick in and your field data wont get sent.
# - this is why people should dev with strict ON, then turn it off later. This may in fact be what strict is FOR.
# - we're not going to try and be more helpful here because we could have to pick an encoding etc to compare the strings. Too much pain.
# - just tell devs to dev with strict on.


# --- Zero-value compactness check ---

def test_schema_pack_zeroval():
    # Testing this buffer...
    number1_zero_header = "17 01"
    string1_zero_header = "14 02"
    bool1_zero_header   = "15 03"
    buf_zv_hex = " ".join([number1_zero_header, string1_zero_header, bool1_zero_header])
    buf_zv = SBytes(buf_zv_hex)

    # ...against this data
    test_zv_data = dict(bool1=False, number1=0, string1=u"")

    buf = schema_pack(TEST_SCHEMA_1, test_zv_data)
    assert buf_zv == buf


# --- Nesting UX Test ---

OUTER_SCHEMA = (
    (B3_BYTES,          "bytes1",  1),
    (B3_SVARINT,        "signed1", 2),
    (B3_COMPOSITE_DICT, "inner1",  3)
    )


def test_schema_pack_nesting():
    # Testing this buffer...
    bytes1_hex  = "53 01 0a 6f 75 74 65 72 62 79 74 65 73"   # header + 'outerbytes'
    signed1_hex = "58 02 02 a3 13"                          # header + encode_svarint(-1234)
    inner_hex   = "51 03 06 17 01 14 02 15 03"              # header + buffer output from the zeroval test
    test_outer_buf = SBytes(" ".join([bytes1_hex, signed1_hex, inner_hex]))

    # ...against this data
    inner_data = dict(bool1=False, number1=0, string1=u"")
    inner1 = schema_pack(TEST_SCHEMA_1, inner_data)
    outer_data = dict(bytes1=b"outerbytes", signed1=-1234, inner1=inner1)
    outer_buf = schema_pack(OUTER_SCHEMA, outer_data)

    print(hexdump(outer_buf))

    assert outer_buf == test_outer_buf


# ==========
# = unpack_recurse can unpack the buffer output from test_schema_pack_nesting() !

# >>> from b3 import unpack
# >>> from b3.utils import SBytes
# >>> j = "53 01 0a 6f 75 74 65 72 62 79 74 65 73 58 02 02 a3 13 51 03 06 17 01 14 02 15 03"     # <-- output from above
# >>> k = SBytes(j)
# >>> k
# 'S\x01\nouterbytesX\x02\x02\xa3\x13Q\x03\x06\x17\x01\x14\x02\x15\x03'

# >>> unpack(k, 0, len(k))
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "b3\composite_dynamic.py", line 85, in unpack
#     raise TypeError("Expecting list or dict container type first in message, but got %i" % (data_type,))
# TypeError: Expecting list or dict container type first in message, but got 3

# >>> from b3.composite_dynamic import unpack_recurse
# >>> out = {}
# >>> unpack_recurse(out, k, 0, len(k))
# >>> out

# {1: 'outerbytes', 2: -1234, 3: {1: 0, 2: u'', 3: False}}



#
# # --- Unpack/Decoder tests ---
#
# def test_schema_unpack_1():
#     out1 = schema_unpack(TEST_SCHEMA_1, test1_buf, 0, len(test1_buf))
#     assert out1 == test1



# things to test:
# - error of passing an empty schema - actually this will blow up with supplied key not in schema

# supplied key not in schema is good because will force the user to explicitely put in None values.s

# Policy: its up to the user to save a copy of incoming messages for cases where there are more fields than there are in the schema.





