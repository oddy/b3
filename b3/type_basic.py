
# Codecs for basic/simple types

import struct, math

from b3.utils import IntByteAt, VALID_INT_TYPES, VALID_STR_TYPES

# Method: Encoders assemble lists of byte-buffers, then b"".join() them. We take advantage of this often for empty/nonexistant fields etc.
# Method: Decoders always take the whole buffer, and an index, and return an updated index.

# Policy: Encoders MAY return no bytes to signify a Compact Zero Value (optional)
# Policy: Decoders MUST accept if index==end and return a Zero value (mandatory)
# Policy: Favouring simplicity over performance by having the type safety checks here.



def encode_utf8(value):
    if not isinstance(value, VALID_STR_TYPES):
        raise TypeError("utf8 only accepts string values")
    return value.encode("utf8")

def decode_utf8(buf, index, end):                   # handles index==end transparently.
    return buf[index:end].decode("utf8")


def encode_s64(value):
    if value == 0:
        return b""
    if not isinstance(value, VALID_INT_TYPES):
        raise TypeError("s64 only accepts integer values")
    return struct.pack("<q", value)

def decode_s64(buf, index, end):
    if index == end:
        return 0
    if end-index != 8:
        raise ValueError("B3_S64 data size isn't 8 bytes")
    return struct.unpack("<q", buf[index:index+8])[0]


def encode_float64(value):
    if not isinstance(value, float):
        raise TypeError("float64 only accepts float values")
    if value == 0.0:
        return b""
    return struct.pack("<d", value)

def decode_float64(buf, index, end):
    if index == end:
        return 0.0
    if end-index != 8:
        raise ValueError("B3_FLOAT64 data size isn't 8 bytes")
    return struct.unpack("<d", buf[index:index+8])[0]





# In: a python complex number object. Must have real and imag properties
def encode_complex(value):
    if not isinstance(value, complex):
        raise TypeError("complex only accepts complex types")
    if value == 0j:
        return b""
    return struct.pack("<dd", value.real, value.imag)

def decode_complex(buf, index, end):
    if index == end:
        return 0j
    if end-index != 16:
        raise ValueError("B3_COMPLEX data size isn't 16 bytes")
    return complex(*struct.unpack("<dd",buf[index:index+16]))


# Note: the 'end' parameter for the decoders is the index of the start of the NEXT object, which == out object's SIZE if index==0
#         so yes, decode(blah, 0, len(blah)) is correct when testing.
#         and index==end means there is no data at all.

# Note: Endianness - there appears to be no difference between <q and >q performance-wise on py2 or py3.
# Note: there is no Null type or null-type codec, instead item headers have a null-flag. See item_header module for more info.
# Policy: Favouring simplicity over performance by having the type safety checks here.
# i.e. dynamic shouldn't need type safety checks because it's types are aquired from the guess_type() function rather than directly from the user
# but splitting out the type checks from the codecs will bloat the code so we're not doing that.

# todo: length checks with the end parameter?  we're mostly EAFP-ing this for now.


