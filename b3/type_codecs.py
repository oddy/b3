# Mapping the data type numbers to codec functions.

import decimal, datetime  # for the zero value table

from b3.datatypes import *

# --- Codec functions ---
from b3 import type_basic
from b3 import type_varint
from b3 import type_decimal
from b3 import type_sched


ENCODERS = {
    UTF8: type_basic.encode_utf8,
    FLOAT64: type_basic.encode_float64,
    COMPLEX: type_basic.encode_complex,
    UVARINT: type_varint.encode_uvarint,
    SVARINT: type_varint.encode_svarint,
    DECIMAL: type_decimal.encode_decimal,
    SCHED: type_sched.encode_sched,
}

DECODERS = {
    UTF8: type_basic.decode_utf8,
    FLOAT64: type_basic.decode_float64,
    COMPLEX: type_basic.decode_complex,
    UVARINT: type_varint.codec_decode_uvarint,
    SVARINT: type_varint.codec_decode_svarint,
    DECIMAL: type_decimal.decode_decimal,
    SCHED: type_sched.decode_sched,
}

# Policy: If there's no codec for a type, then it's a yield-as-bytes.
#         (for e.g. schema-composite, and the actual BYTES type, and unknown types)
# Policy: NULL is not a specific type, it is a flag in the item header.
#         (So any item can be NULL and also STILL have a type, on the wire)

ZERO_VALUE_TABLE = {
    BYTES: b"",
    UTF8: "",
    BOOL: False,
    UVARINT: 0,
    SVARINT: 0,
    U64: 0,
    S64: 0,
    FLOAT64: 0.0,
    DECIMAL: decimal.Decimal("0.0"),
    SCHED: datetime.datetime(1, 1, 1),  # somewhat arbitrary, but matches golang zero-value time
    LIST: [],  # Note: unused because the composite modules have their own logic
    DICT: {},  # Note: for list and dict.
    COMPLEX: 0j,
}
