
# Mapping the data type numbers to codec functions.


import datetime, decimal
from six import PY2

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
    B3_UVARINT  : (type_varint.codec_encode_uvarint,  type_varint.codec_decode_uvarint),  # note codec-specific varint decoder function
    B3_SVARINT  : (type_varint.codec_encode_svarint,  type_varint.codec_decode_svarint),  # note codec-specific varint decoder function
    B3_DECIMAL  : (type_decimal.encode_decimal, type_decimal.decode_decimal),
    B3_SCHED    : (type_sched.encode_sched,     type_sched.decode_sched),
}


# --- Python-Obj to B3-Type guesser for dynamic-composite packer ---

# Policy: some types are guessed differently depending on value eg SVARINT for negative numbers.
# todo: supply fast/compact switch to GuessType, its the only place that needs it.
# Note no NONE type because that's handled by the is_null bit.

# todo: guess_type should be tested more rigourously

def guess_type(obj):
    if isinstance(obj, bytes):                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.
        return B3_BYTES

    if PY2 and isinstance(obj, unicode):        # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):                    # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    if obj is True or obj is False:             # Note: make sure this check is BEFORE int checks!
        return B3_BOOL                          # Note: because bools are a subclass of int (!?) in python :S

    if isinstance(obj, int):
        if obj >= 0:    return B3_UVARINT
        else:           return B3_SVARINT
        # return B3_INT64                        # currently unused by dynrec. needs Fast/Compact policy switch.

    if PY2 and isinstance(obj, long):
        return B3_SVARINT                        # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, dict):
        return B3_COMPOSITE_DICT

    if isinstance(obj, list):
        return B3_COMPOSITE_LIST

    if isinstance(obj, float):
        return B3_FLOAT64                       # Policy: we are NOT auto-converting stuff to DECIMAL, callers responsibility

    if isinstance(obj, decimal.Decimal):
        return B3_DECIMAL

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return B3_SCHED
        # return B3_STAMP64                     # stamp64 takes floats and ints, not datetimes. Not used by dynamic.

    if isinstance(obj, complex):
        return B3_COMPLEX

    raise TypeError('Could not map type of object %r to a viable B3 type' % type(obj))

