
# Codecs for basic/simple types

import struct, math

from utils import IntByteAt, VALID_INT_TYPES, VALID_STR_TYPES

# Note: the 'end' parameter for the decoders is the index of the start of the NEXT object, which == out object's SIZE if index==0
#         so yes, decode(blah, 0, len(blah)) is correct when testing.
#         and index==end does mean there is no data at all.

# Note: Endianness - there's no difference between <q and >q performance-wise on py2 or py3.
# Note: there is no Null type or null-type codec, instead item headers have a null-flag. See item_header module for more info.
# Policy: Favouring simplicity over performance by having the type safety checks here.
# i.e. dynamic shouldn't need type safety checks because it's types are aquired from the guess_type() function rather than directly from the user
# but splitting out the type checks from the codecs will bloat the code so we're not doing that.
# todo: length checks with the end parameter.

def encode_bool(value):
    value = bool(value)
    return b"\x01" if value else b"\x00"

def decode_bool(buf, index, end):
    x,index = IntByteAt(buf, index)
    return {0:False, 1:True}[x]


def encode_utf8(value):
    if not isinstance(value, VALID_STR_TYPES):
        raise TypeError("utf8 only accepts string values")
    return value.encode("utf8")

def decode_utf8(buf, index, end):
    return buf[index:end].decode("utf8")


def encode_int64(value):
    if not isinstance(value, VALID_INT_TYPES):
        raise TypeError("int64 only accepts integer values")
    return struct.pack("<q", value)

def decode_int64(buf, index, end):
    return struct.unpack("<q", buf[index:index+8])[0]



def encode_float64(value):
    if not isinstance(value, float):
        raise TypeError("float64 only accepts float values")
    return struct.pack("<d", value)

def decode_float64(buf, index, end):
    return struct.unpack("<d", buf[index:index+8])[0]



# In:  unix-epoch-nanoseconds integer.
# Note: we also accept floats for convenience with e.g. time.time.
def encode_stamp64(value):
    if isinstance(value, float):
        value = math.trunc(value * 1e9)
    elif not isinstance(value, VALID_INT_TYPES):
        raise TypeError("stamp64 only accepts float or integer values")
    return struct.pack("<q", value)

# Note: we only yield integer nanoseconds. Up to the caller to float-er-ize it if they need.
def decode_stamp64(buf, index, end):
    return struct.unpack("<q", buf[index:index+8])[0]


# In: a python complex number object. Must have real and imag properties
def encode_complex(value):
    if not isinstance(value, complex):
        raise TypeError("complex only accepts complex types")
    return struct.pack("<dd", value.real, value.imag)

def decode_complex(buf, index, end):
    return complex(*struct.unpack("<dd",buf[index:index+16]))




