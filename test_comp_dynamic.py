
import pytest, copy

from .utils import SBytes
from .datatypes import *
from .composite_dynamic import pack, unpack, unpack_recurse
from .hexdump import hexdump

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# Policy: small-scale bottom-up-assembly data items.
# bottom-up-assmbly means the size-in-bytes of everything is always known.
# Counter-Rationale: the only use cases blair and i could think of for unknown-size items are:
# 1) Huge datastructures (e.g. qsa tables) which will have their own sizing,
# 2) e.g. tcp comms big-long-streaming which should always be chunked anyway!


# --- Shared test data ---

# This structure should test all code paths in pack, unpack, and unpack_recurse.

test1_data = {10:0, 11:b"foo", 12:[True,False,False,True], 13:{9:8, 7:6}, 14:None }

buf10 = "17 0a"                                             #  uvarint, key=10, len=0 (CZV)
buf11 = "53 0b 03 66 6f 6f"                                 #  bytes,   key=11, len 3, b"foo"
buf12_list_bytes = "45 01 01 05 05 45 01 01"                #  True ends up being "45 01 01" and False is "05" because CZV.
buf12 = "52 0c 08 " + buf12_list_bytes                      #  list,    key=12, len=8
buf13_dict_bytes = "57 09 01 08 57 07 01 06"                #  items for 9:8 and 7:6
buf13 = "51 0d 08 " + buf13_dict_bytes                      #  dict,    key=13, len=8
buf14 = "93 0e"                                             #  [bytes]**  key=14, is_null=True
outer_header = "41 20"                                      #  dict, no key, len=32

test1_buf = SBytes(" ".join([outer_header, buf10, buf11, buf12, buf13, buf14]))

# Policy: Packer: ** we interpret Nones coming into pack from the user, as BYTES types.
# (Because we dont have any schema info to determine what the type actually is.)
# If this is a problem, we recommend switching to the schema-based API.

# --- Pack/Encoder tests ---

# None, bytes, list, dict, a-codec-type, and with-header & without-header are all the code paths in pack().

def test_dyna_pack_kitchen_sink():
    out1_buf = pack(test1_data)
    assert out1_buf == test1_buf

def test_dyna_pack_kitchen_sink_no_header():
    out1_buf = pack(test1_data, with_header=False)
    assert out1_buf == test1_buf[2:]


# Unpack calls unpack_recurse once it's read the initial header to see what the topmost container is, and created that.
# unpack_recurse unpacks the buffer it's given, into the container it's given.

# --- Unpack tests ---

# def test_dyna_unpack_index_over_end():            # todo: currently n/a as unpack isn't taking an end argument.
#     with pytest.raises(ValueError):
#         unpack(b"", 0, 0)

def test_dyna_unpack_header_only_list():
    hdr_buf = SBytes("02")              # no key, no data, list type.
    assert unpack(hdr_buf,0) == []

def test_dyna_unpack_header_only_dict():
    hdr_buf = SBytes("01")              # no key, no data, dict type.
    assert unpack(hdr_buf,0) == {}

def test_dyna_unpack_header_only_invalid_type():
    hdr_buf = SBytes("05")              # no key, no data, bool type. (Error!)
    with pytest.raises(TypeError):
        assert unpack(hdr_buf,0) == {}

# --- Unpack_recurse tests ---

# This one should test all unpack and unpack_recurse code paths if the data above is used.

def test_dyna_unpack_kitchen_sink():
    assert unpack(test1_buf, 0) == test1_data

def test_dyna_unpack_recurse_invalid_container():
    with pytest.raises(TypeError):
        unpack_recurse(None, SBytes("93 0e"),0,2)               # passing None instead of a list or dict.


# --- Round Trip ---
def test_dyna_roundtrip():
    assert unpack(pack(test1_data),0) == test1_data


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

