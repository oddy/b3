
import pytest, copy

from .utils import SBytes
from .datatypes import *
from .composite_schema import schema_pack, schema_unpack, UnwantedFieldError, MissingFieldError
from .hexdump import hexdump

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---


# --- Test data ---

TEST_SCHEMA_1 = (
    (B3_UVARINT, u"number1", 1),
    (B3_UTF8,    u"string1", 2),
    (B3_BOOL,    u"bool1",   3)
)

test1 = dict(number1=69, string1=u"foo", bool1=True)

number1_data   = u"45"                   # encode_uvarint(69)
number1_header = u"57 01 01"             # encode_header(B3_UVARINT, key=1, data_len=1)
string1_data   = u"66 6f 6f"             # encode_utf8(u"foo")
string1_header = u"54 02 03"             # encode_header(B3_UTF8, key=2, data_len=3)
bool1_data     = u"01"                   # encode_bool(True)
bool1_header   = u"55 03 01"             # encode_header(B3_BOOL, key=3, data_len=1)



test1_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header, bool1_data])
test1_buf = SBytes(test1_hex)


# --- Pack/Encoder tests ---

def test_schema_pack_comp():
    out1_buf = schema_pack(TEST_SCHEMA_1, test1)
    # print(u"\n%s\n%s\n" % (hexdump(test1_buf), hexdump(out1_buf)))
    assert out1_buf  == test1_buf

def test_schema_pack_dictcheck():
    with pytest.raises(TypeError):
        schema_pack(TEST_SCHEMA_1, [])

# Field found in input dict which does not exist in schema. Default=ignore it, strict=raise exception.
#
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

# Field missing from input dict but exists in schema, output present with null/None value.

def test_schema_pack_field_missing():
    test2 = copy.copy(test1)
    del test2['bool1']

    bool1_header_null_value   = u"95 03"                # encode_header(B3_BOOL, key=3, is_null=True)
    test2_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header_null_value])  # note no data for bool1
    test2_buf = SBytes(test2_hex)

    buf = schema_pack(TEST_SCHEMA_1, test2)
    assert buf == test2_buf





#
#
#
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

#

# todo: two-level manually behaviour.  - returning BYTES for composites.

# todo: present-member

# todo: fully strictness checking on the parser side.

