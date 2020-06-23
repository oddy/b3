
# Mapping the data type numbers to codec functions.

from b3.datatypes import *

# --- Codec functions ---
from b3 import type_basic
from b3 import type_varint
from b3 import type_decimal
from b3 import type_sched

# Policy: If there's no codec for a type, then it's a yield-as-bytes. (for e.g. schema-composite, and the actual B3_BYTES type)
# Policy: NULL is not a specific type, it is a flag in the item header. (So any item can be NULL and also STILL have a type, on the wire)

CODECS = {
    B3_BOOL     : (type_basic.encode_bool,      type_basic.decode_bool),
    B3_UTF8     : (type_basic.encode_utf8,      type_basic.decode_utf8),
    B3_INT64    : (type_basic.encode_int64,     type_basic.decode_int64),
    B3_FLOAT64  : (type_basic.encode_float64,   type_basic.decode_float64),
    B3_STAMP64  : (type_basic.encode_stamp64,   type_basic.decode_stamp64),
    B3_COMPLEX  : (type_basic.encode_complex,   type_basic.decode_complex),
    B3_UVARINT  : (type_varint.codec_encode_uvarint,  type_varint.codec_decode_uvarint),  # note codec-specific varint functions
    B3_SVARINT  : (type_varint.codec_encode_svarint,  type_varint.codec_decode_svarint),  # note codec-specific varint functions
    B3_DECIMAL  : (type_decimal.encode_decimal, type_decimal.decode_decimal),
    B3_SCHED    : (type_sched.encode_sched,     type_sched.decode_sched),
}

