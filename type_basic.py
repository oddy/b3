
import struct, math

from   six import PY2, int2byte

from   datatypes import IntByteAt

VALID_STR_TYPE = unicode if PY2 else str
if PY2:     VALID_INT_TYPES = (int, long)
else:       VALID_INT_TYPES = (int,)


# NOTE: we will write these as full functions for now for testing, then shortcut some of the simpler ones later.
# Note: there's no difference between <q and >q performance-wise on py2 or py3.
# Note: uvarint and svarint are handled by type_varint.py atm.

def encode_null(value):
    if value is not None:
        raise TypeError('value is not None')
    return b''

def decode_null(buf, index, end):
    return None,index



def encode_bool(value):
    value = bool(value)
    return b'\x01' if value else b'\x00'

def decode_bool(buf, index, end):
    x,index = IntByteAt(buf, index)
    return {0:False, 1:True}[x], index



def encode_bytes(value):
    if not isinstance(value, bytes):                            # todo: bytearray
        raise TypeError("bytes only accepts byte values")
    return value

def decode_bytes(buf, index, end):
    return buf[index:end], end



def encode_utf8(value):
    if not isinstance(value, VALID_STR_TYPE):
        raise TypeError("utf8 only accepts string values")
    return value.encode("utf8")

def decode_utf8(buf, index, end):
    return buf[index:end].decode("utf8"), end




def encode_int64(value):
    if not isinstance(value, VALID_INT_TYPES):
        raise TypeError("int64 only accepts integer values")
    return struct.pack("<q", value)

def decode_int64(buf, index, end):
    return struct.unpack("<q", buf[index:index+8])[0], index+8



def encode_float64(value):
    if not isinstance(value, float):
        raise TypeError("float64 only accepts float values")
    return struct.pack("<d", value)

def decode_float64(buf, index, end):
    return struct.unpack("<d", buf[index:index+8])[0], index+8



# In:  unix-epoch-nanoseconds integer. Note: we also accept floats for convenience with e.g. time.time.
def encode_stamp64(value):
    if isinstance(value, float):
        value = math.trunc(value * 1e9)
    if not isinstance(value, VALID_INT_TYPES):
        raise TypeError("stamp64 only accepts float or integer values")
    return struct.pack("<q", value)

# Note: we only yield integer nanoseconds. Up to the caller to float-er-ize it if they need.

def decode_stamp64(buf, index, end):
    return struct.unpack("<q", buf[index:index+8])[0], index+8




# In: a python complex number object. Must have real and imag properties
def encode_complex(value):
    if not isinstance(value, complex):
        raise TypeError("complex only accepts complex types")
    return struct.pack("<dd", value.real, value.imag)

def decode_complex(buf, index, end):
    return complex(*struct.unpack("<dd",buf[index:index+16])), index+16




