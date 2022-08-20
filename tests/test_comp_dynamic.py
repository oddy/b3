import datetime, decimal
import pytest

from b3.utils import SBytes
from b3.composite_dynamic import pack, unpack, unpack_into

# Policy: small-scale bottom-up-assembly. (See format doc)

# B3 software Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

# Item header & data structure is
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

# --- Shared test data ---

# This structure should test all code paths in pack, unpack, and unpack_into.

test1_data = {
    10: 0,
    11: b"foo",
    12: [True, False, False, True],
    13: {9: 8, 7: 6},
    14: None,
}

buf10 = "41 0a"  # svarint, key=10, len=0 (CZV)
buf11 = "09 0b 03 66 6f 6f"  # bytes,   key=11, len 3, b"foo"
buf12_list_bytes = "2c 28 28 2c"  # True ends up being "c2" and False is "82"
buf12 = "d9 0c 04 " + buf12_list_bytes  # list,    key=12, len=4
buf13_dict_bytes = "49 09 01 10 49 07 01 0c"  # items for 9:8 and 7:6
buf13 = "e9 0d 08 " + buf13_dict_bytes  # dict,    key=13, len=8
buf14 = "05 0e"  # [bytes]**  key=14, is_null=True
outer_header = "e8 1c"  # dict, no key, len=28
test1_buf = SBytes(" ".join([outer_header, buf10, buf11, buf12, buf13, buf14]))

# Policy: Packer: ** we interpret Nones coming into pack from the user, as BYTES types.
#         (Because we dont have any schema info to determine what the type actually is.)
#         If this is a problem, we recommend switching to the schema-based API.

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
    hdr_buf = SBytes("d0")  # no key, no data, list type.
    assert unpack(hdr_buf, 0) == []


def test_dyna_unpack_header_only_dict():
    hdr_buf = SBytes("e0")  # no key, no data, dict type.
    assert unpack(hdr_buf, 0) == {}


def test_dyna_unpack_header_only_invalid_type():
    hdr_buf = SBytes("50")  # no key, no data, bool type. (Error!)
    with pytest.raises(TypeError):
        assert unpack(hdr_buf, 0) == {}


# --- Unpack_recurse tests ---

# This one should test all unpack and unpack_into code paths if the data above is used.


def test_dyna_unpack_dict():
    assert unpack(test1_buf, 0) == test1_data


def test_dyna_unpack_recurse_invalid_container():
    with pytest.raises(TypeError):
        unpack_into(None, SBytes("53 0e"), 0, 2)  # passing None instead of a list or dict.


# --- Round Trip ---
def test_dyna_roundtrip_dict():
    assert unpack(pack(test1_data), 0) == test1_data


def test_dyna_roundtrip_into():
    buf = pack(test1_data, with_header=False)
    out = dict()
    unpack_into(out, buf, 0, len(buf))
    assert out == test1_data


def test_dyna_roundtrip_list():
    test_list = [1, 2, 3, 4, 5, u"a", u"b", b"xx"]
    assert unpack(pack(test_list), 0) == test_list


data_dyna_types = [
    None,
    b"foo",
    u"bar",
    True,
    -69,  # note: only SVARINT tested here because of guess_type policy
    2.318,
    decimal.Decimal("3.8"),
    datetime.datetime.now(),
    {1: 2},
    [3, 4],
    4j,
]


def test_dyna_roundtrip_all_guess_types():
    # dynamic uses dict, list, bytes, utf8, bool, svarint, float64, decimal, sched, complex
    # dynamic currently does NOT use non-svarint number types
    assert unpack(pack(data_dyna_types), 0) == data_dyna_types


def test_dyna_roundtrip_all_guess_types_toplevel_dict():
    DX = dict(top=data_dyna_types)
    assert unpack(pack(DX), 0) == DX


# --- Weird cases ---


def test_dyna_dict_none_key():
    c = {None: 3}  # annoyingly, this is allowed in python
    buf = pack(c)
    out = unpack(buf, 0)
    assert out == c  # but still works fine.


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
