
# Python-Obj to B3-Type guesser for composite_dynamic (pack)

import datetime, decimal
from six import PY2

from b3.datatypes import *

# Policy: Currently guessed types are fixed and 1:1 with python types.
# There is/was an idea to have guess_type select the 'best' type based on value (e.g. SVARINT or UVARINT depending on sign)
# But that would make interop difficult between the Dynamic and Schema packers, so we've dropped it for now.
# The 'best type' selector would have 3 settings -
# 'fixed' (default, as now), 'compact' (e.g. prefer var-types for small numbers), 'fast' (prefer the xxx64 types)

# Policy: we are NOT auto-converting stuff to DECIMAL, callers responsibility
# because we'd have to fix a precision for the user and i dont know if we want to be opinionated about that.
# just because I hate IEEE754 doesnt mean any one else does.

# Note: no NULL type - the item header has a NULL flag instead. More info there.

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
        return B3_SVARINT                       # Policy: fixed to svarint to make this deterministic for better interop.
                                                # alternatives: uvarint, int64
    if PY2 and isinstance(obj, long):
        return B3_SVARINT                       # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, dict):
        return B3_COMPOSITE_DICT

    if isinstance(obj, list):
        return B3_COMPOSITE_LIST

    if isinstance(obj, float):
        return B3_FLOAT64

    if isinstance(obj, decimal.Decimal):
        return B3_DECIMAL

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return B3_SCHED
        # return B3_STAMP64                     # stamp64 takes floats and ints, not datetimes. Not used by dynamic.

    if isinstance(obj, complex):
        return B3_COMPLEX

    raise TypeError('Could not map type of object %r to a viable B3 type' % type(obj))

