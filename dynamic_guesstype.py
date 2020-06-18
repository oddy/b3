
import datetime, decimal
from six import PY2
from datatypes import *


# Policy: some types are guessed differently depending on value eg SVARINT for negative numbers.
# Policy: supply fast/compact switch to GuessType, maybe it can be the only place that now needs it!

# Note no NONE type because that's handled by the is_null bit.

def guess_type(obj):
    if isinstance(obj, bytes):                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.
        return B3_BYTES

    if PY2 and isinstance(obj, unicode):        # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):                    # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    if isinstance(obj, int):
        if obj >= 0:    return B3_UVARINT
        else:           return B3_SVARINT
        # return B3_INT64                        # currently unused by dynrec. needs Fast/Compact policy switch.

    if obj in [True, False]:
        return B3_BOOL

    if PY2 and isinstance(obj, long):
        return B3_SVARINT                        # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, dict):
        return B3_COMPOSITE_DICT

    if isinstance(obj, list):
        return B3_COMPOSITE_LIST

    # we dont use B3_BAG here

    if isinstance(obj, float):
        return B3_FLOAT64                       # Policy: we are NOT auto-converting stuff to DECIMAL, callers responsibility

    if isinstance(obj, decimal.Decimal):
        return B3_DECIMAL

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return B3_SCHED
        # return B3_STAMP64                     # stamp64 takes floats and ints, not datetimes. Not used by dynrec.

    if isinstance(obj, complex):
        return B3_COMPLEX

    raise NotImplementedError('guess_type unknown type %r' % type(obj))

