import struct, decimal, zlib, time
import six
from   six import PY2, int2byte
import datetime
from pprint import pprint

# Note: do NOT have a module named types.py. Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# So we don't use the end_index here, because varints are self-sizing.
# todo: the whole thing with end comes down to container-sizing and whether we're security checking known sizes against end or not.
# todo: really its do we take end as a parameter or return it out as an updated index? We don't need both.
# todo: only decimal decode needs end as a parameter. Everything else is either too simple (no optional parts) or too complex (many internal presence flags for optional components)


# --- Bag end marker ---
B3_END = 0        # end marker. Always 1 byte, always \x00

# --- Structure types ---
B3_BAG = 1        # Our single multipurpose composite type, structured: [item][item][B3_END]
B3_BAG_LIST = 2   # same as BAG on wire, acts as hint to parser to yield a list-like obj where possible
B3_BAG_DICT = 3   # same as BAG on wire, acts as hint to parser to yield a dict-like obj where possible

# --- Tests not done ---
B3_NULL     = 6    # None.                                                      for None.
B3_BOOL     = 5    # True or False.                                             for bool.
B3_BYTES    = 4    # List of bytes (bytearray?).           Note: str in py2.    for bytes.
B3_UTF8     = 7    # UTF8 byte strings.                    for str in py3 and unicode in py2.

B3_INT64    = 8    # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT  = 9    # unsigned varint                       slower & small/large for ints.
B3_SVARINT  = 10   # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python
B3_FLOAT64  = 12   # IEEE754 64bit signed float.           faster & medium      for floats.
B3_STAMP64  = 13   # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time. (ie, timestamps gotten with now() and friends) time.time() (yr 1678-2262)
B3_COMPLEX  = 15    # encoded as 2 float64s.

# --- TESTS DONE ---
B3_SCHED    = 14   # [some sort of]LOCAL time, offset TO utc, TZname.              for user-schedule local time. (ie, times gotten from user input, appointments and schedules.)
B3_DECIMAL  = 11   # Arbitrary Precision decimals.         slower & compact     for decimal.


VALID_STR_TYPES = (unicode,) if PY2 else (str,)
if PY2:     VALID_INT_TYPES = (int, long)
else:       VALID_INT_TYPES = (int,)



# in: some object
# out: type code or NotImplementedError

# do the compact/fast thing here.
# make it so that the Parser is fan-in only

def GuessType(obj):
    if obj is None:
        return B3_NULL

    if obj in [True, False]:
        return B3_BOOL

    if isinstance(obj, bytes):                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.
        return B3_BYTES

    if six.PY2 and isinstance(obj, unicode):        # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):                    # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    # todo: optimal selection for the types below here, depending on value, needs to be standardized.

    if isinstance(obj, int):
        if obj >= 0:    return B3_UVARINT
        else:           return B3_SVARINT
        # return B3_INT64

    if six.PY2 and isinstance(obj, long):
        return B3_SVARINT                        # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, float):
        return B3_FLOAT64
        # return B3_BIGDEC

    if isinstance(obj, datetime):
        return B3_STAMP64
        # return B3_SCHED

    raise NotImplementedError('Unknown type %r' % type(obj))



# Like six.byte2int but buffer-aware and actually works
def IntByteAt(buf, index):
    if not PY2:
        return buf[index], index+1
    else:
        return ord(buf[index]), index+1

