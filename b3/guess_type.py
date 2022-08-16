# Python-Obj to B3-Type guesser for composite_dynamic (pack)

import datetime, decimal
from six import PY2

from b3.datatypes import *

# policy: Weird edge case: if the encoder gets a None, we consider that B3_BYTES, because
#         the header needs to encode *something* as the data type.
# policy: in practice None supercedes data-type checking in dynamic and in the schema packer,
#         so this should be ok.


def guess_type(obj):
    if obj is None:
        return B3_BYTES

    if isinstance(obj, bytes):  # Note this will catch also *str* on python2.
        return B3_BYTES

    if PY2 and isinstance(obj, unicode):  # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):  # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    if obj is True or obj is False:  # Note: make sure this check is BEFORE int checks!
        return B3_BOOL  # Note: because bools are a subclass of int (!?) in python :S

    if isinstance(obj, int):
        return B3_SVARINT  # Policy: fixed to svarint to make this deterministic for better interop.

    if PY2 and isinstance(obj, long):
        return B3_SVARINT  # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, dict):
        return B3_DICT

    if isinstance(obj, list):
        return B3_LIST

    if isinstance(obj, float):
        return B3_FLOAT64

    if isinstance(obj, decimal.Decimal):
        return B3_DECIMAL

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return B3_SCHED

    if isinstance(obj, complex):
        return B3_COMPLEX

    raise TypeError("Could not map type of object %r to a viable B3 type" % type(obj))


# Policy: Currently guessed types are fixed and 1:1 with python types.
# - There is/was an idea to have guess_type select the 'best' type based on value (e.g. SVARINT or UVARINT depending on sign)
# - But that would make interop difficult between the Dynamic and Schema packers, so we've dropped it for now.
# The 'best type' selector would have 3 settings -
# 'fixed' (default, as now), 'compact' (e.g. prefer var-types for small numbers), 'fast' (prefer the xxx64 types)
# The wastefulness of using svarint for everything hurts a little, but compactness-obsessed people should be using schemas anyway.

# Policy: we are NOT auto-converting stuff to DECIMAL, callers responsibility
# - because we'd have to fix a precision for the user and i dont know if we want to be opinionated about that.
# - just because I hate IEEE754 doesnt mean any one else does.

# Note: no NULL type - the item header has a NULL flag instead. More info in item_header.
