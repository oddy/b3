# Mapping the data type numbers to codec functions.

import decimal, datetime  # for the zero value table

from b3.datatypes import *

# --- Codec functions ---
from b3 import type_basic
from b3 import type_varint
from b3 import type_decimal
from b3 import type_sched


ENCODERS = {
    B3_UTF8: type_basic.encode_utf8,
    B3_FLOAT64: type_basic.encode_float64,
    B3_COMPLEX: type_basic.encode_complex,
    B3_UVARINT: type_varint.codec_encode_uvarint,
    B3_SVARINT: type_varint.codec_encode_svarint,
    B3_DECIMAL: type_decimal.encode_decimal,
    B3_SCHED: type_sched.encode_sched,
}

DECODERS = {
    B3_UTF8: type_basic.decode_utf8,
    B3_FLOAT64: type_basic.decode_float64,
    B3_COMPLEX: type_basic.decode_complex,
    B3_UVARINT: type_varint.codec_decode_uvarint,
    B3_SVARINT: type_varint.codec_decode_svarint,
    B3_DECIMAL: type_decimal.decode_decimal,
    B3_SCHED: type_sched.decode_sched,
}

# Policy: If there's no codec for a type, then it's a yield-as-bytes. (for e.g. schema-composite, and the actual B3_BYTES type)
# Policy: NULL is not a specific type, it is a flag in the item header. (So any item can be NULL and also STILL have a type, on the wire)

#
# ZERO_VALUE_TABLE = {
#     B3_BYTES: b"",
#     B3_UTF8: "",
#     B3_BOOL: False,
#     B3_UVARINT: 0,
#     B3_SVARINT: 0,
#     B3_U64: 0,
#     B3_S64: 0,
#     B3_FLOAT64: 0.0,
#     B3_DECIMAL: decimal.Decimal("0.0"),
#     B3_SCHED: datetime.datetime(1, 1, 1),  # somewhat arbitrary, but matches golang zero-value time
#     B3_LIST: [],
#     B3_DICT: {},
#     B3_COMPLEX: 0j,
# }


ZERO_VALUE_TABLE = {
    B3_BYTES: b"",
    B3_UTF8: "",
    B3_BOOL: False,
    B3_UVARINT: 0,            # why does changing this to a string cause fallthrough to codec zero value prep-to-remove?
    B3_SVARINT: 0,
    B3_U64: 0,
    B3_S64: 0,
    B3_FLOAT64: 0.0,
    B3_DECIMAL: decimal.Decimal("0.0"),
    B3_SCHED:  datetime.datetime(1, 1, 1),  # somewhat arbitrary, but matches golang zero-value time
    B3_LIST: [],          # Note: unused  ??
    B3_DICT: {},          # Note: unused  ??
    B3_COMPLEX: 0j,
}
