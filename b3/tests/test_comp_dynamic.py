
import pytest

from b3.utils import SBytes
from b3.composite_dynamic import pack, unpack, unpack_into

# B3 software Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---


# Policy: small-scale bottom-up-assembly. (See format doc)


# --- Shared test data ---

# This structure should test all code paths in pack, unpack, and unpack_into.

test1_data = {10:0, 11:b"foo", 12:[True,False,False,True], 13:{9:8, 7:6}, 14:None }

buf10 = "14 0a"                                             # svarint, key=10, len=0 (CZV)
buf11 = "90 0b 03 66 6f 6f"                                 # bytes,   key=11, len 3, b"foo"
buf12_list_bytes = "82 01 01 02 02 82 01 01"                # True ends up being "85 01 01" and False is "05" because CZV.
buf12 = "9d 0c 08 " + buf12_list_bytes                      # list,    key=12, len=8
buf13_dict_bytes = "94 09 01 10 94 07 01 0c"                # items for 9:8 and 7:6
buf13 = "9e 0d 08 " + buf13_dict_bytes                      # dict,    key=13, len=8
buf14 = "50 0e"                                             # [bytes]**  key=14, is_null=True
outer_header = "8e 20"                                      # dict, no key, len=32

test1_buf = SBytes(" ".join([outer_header, buf10, buf11, buf12, buf13, buf14]))

# Policy: Packer: ** we interpret Nones coming into pack from the user, as BYTES types.
# (Because we dont have any schema info to determine what the type actually is.)
# If this is a problem, we recommend switching to the schema-based API.

# --- Pack/Encoder tests ---

def test_dyna_pack_dict():
    out1_buf = pack(test1_data)
    assert out1_buf == test1_buf

def test_dyna_pack_dict_no_header():
    out1_buf = pack(test1_data, with_header=False)
    assert out1_buf == test1_buf[2:]


# Unpack reads the initial header to see what the topmost container is, creates that, then calls unpack_into
# unpack_into unpacks the buffer it's given, into the container it's given.

# --- Unpack tests ---

def test_dyna_unpack_header_only_list():
    hdr_buf = SBytes("0d")              # no key, no data, list type.
    assert unpack(hdr_buf,0) == []

def test_dyna_unpack_header_only_dict():
    hdr_buf = SBytes("0e")              # no key, no data, dict type.
    assert unpack(hdr_buf,0) == {}

def test_dyna_unpack_header_only_invalid_type():
    hdr_buf = SBytes("05")              # no key, no data, bool type. (Error!)
    with pytest.raises(TypeError):
        assert unpack(hdr_buf,0) == {}

# --- Unpack_recurse tests ---

# This one should test all unpack and unpack_into code paths if the data above is used.

def test_dyna_unpack_dict():
    assert unpack(test1_buf, 0) == test1_data

def test_dyna_unpack_recurse_invalid_container():
    with pytest.raises(TypeError):
        unpack_into(None, SBytes("53 0e"), 0, 2)               # passing None instead of a list or dict.


# --- Round Trip ---
def test_dyna_roundtrip_dict():
    assert unpack(pack(test1_data),0) == test1_data

def test_dyna_roundtrip_into():
    buf = pack(test1_data, with_header=False)
    out = dict()
    unpack_into(out, buf, 0, len(buf))
    assert out == test1_data

def test_dyna_roundtrip_list():
    test_list = [1, 2, 3, 4, 5, u'a', u'b', b'xx']
    assert unpack(pack(test_list),0)  == test_list

def test_dyna_roundtrip_all_types():
    import datetime, decimal
    # dynamic uses dict, list, bytes, utf8, bool, svarint, float64, decimal, sched, complex
    # dynamic currently does NOT use non-svarint number types
    data_dyna_types = [
        {1:2}, [3,4],
        b'foo', u'bar', True,
        -69, 2.318,
        decimal.Decimal('3.8'), datetime.datetime.now(),
        4j,
        None
        ]
    assert unpack(pack(data_dyna_types),0) == data_dyna_types


# --- Weird cases ---

def test_dyna_dict_none_key():
    c = {None : 3}                  # annoyingly, this is allowed in python
    buf = pack(c)
    out = unpack(buf,0)
    assert out == c                 # but still works fine.



# --- Test interop with schema comp ---

# For interop with schema comp you need to use dicts only, with string name keys that match the field names,
# or number keys that match the field numbers. The schema parser skips anything that doesn't have a key, which means lists are out.
# interop is limited by guess_type's value-choosing. Types may change depending on the values given (e.g. -ve integers).

# def test_dyna_pack_interop():
#     inter_data = dict(number1=120, string1=u"hello world", bool1=True)
#     buf = pack(inter_data)
#     print()
#     print(hexdump(buf))
#     print()
#     print(repr(buf))

