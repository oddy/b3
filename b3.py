# Goal:
# JSON-style pack/unpack. Choose compact or fast.       (schema pack/unpack would work like struct pack/unpack in Go)
# Todo: we need a framework for developing and testing our various type formats.
# only the complicated formats need their own functions.
# the simple formats are all in one single function, and we'll test it that way.

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

import struct

from datatypes import *
from varint import *


# "single-item ToBytes packer"
# In:  some sort of python object, and the B3_TYPE we want it to be
# Out: bytes
# This fn will just try and do the packing. Validation or Type-guessing belong in the composite-packer/UX mainloops.
#   also whethe compact or fast is chosen is someone elses problem (because the b3 type wanted is the RESULT of that decision)

# Because "automagically pick the best type for the given value" and "try and shoehorn the given value into the given type" are
# two fundamentally different operations.

PACK_FNS = {
    B3_BYTES    : lambda x : x,
    B3_NULL     : lambda x : b'',
    B3_BOOL     : lambda x : b'\x01' if x else b'\x00',
    B3_UTF8     : lambda x : x.encode('utf8'),

    B3_INT64    : lambda x : struct.pack("<q", x),
    B3_UVARINT  : encode_uvarint,
    B3_SVARINT  : encode_svarint,

    B3_FLOAT64  : lambda x : struct.pack("d", x),
    B3_DECIMAL  : encode_decimal,                           # takes decimal types and float types
    B3_DECIFLOAT: encode_decimal,

    B3_STAMP64  : encode_stamp64,
    B3_SCHED    : encode_sched,

    B3_COMPLEX  : encode_complex,
    }


def PackToBytes(obj, b3type):
    return PACK_FNS[b3type](obj)
