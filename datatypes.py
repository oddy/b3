import struct, decimal, zlib, time
import six
from   six import PY2, int2byte
import datetime
from pprint import pprint
from   varint import encode_uvarint, encode_svarint


# Note: do NOT have a module named types.py. Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# --- Bag end marker ---
B3_END = 0        # end marker. Always 1 byte, always \x00

# --- Structure types ---
B3_BAG = 1        # Our single multipurpose composite type, structured: [item][item][B3_END]
B3_BAG_LIST = 2   # same as BAG on wire, acts as hint to parser to yield a list-like obj where possible
B3_BAG_DICT = 3   # same as BAG on wire, acts as hint to parser to yield a dict-like obj where possible

# --- Basic types ---
B3_NULL     = 6    # None.                                                      for None.
B3_BOOL     = 5    # True or False.                                             for bool.
B3_BYTES    = 4    # List of bytes (bytearray?).           Note: str in py2.    for bytes.
B3_UTF8     = 7    # UTF8 byte strings.                    for str in py3 and unicode in py2.

# --- Funky types ---
B3_INT64    = 8    # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT  = 9    # unsigned varint                       slower & small/large for ints.
B3_SVARINT  = 10   # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python

B3_FLOAT64  = 10   # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL  = 11   # Arbitrary Precision decimals.         slower & compact     for decimal.

B3_STAMP64  = 13   # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time. (ie, timestamps gotten with now() and friends) time.time()
B3_SCHED    = 14   # [some sort of]LOCAL time, offset TO utc, TZname.              for user-schedule local time. (ie, times gotten from user input, appointments and schedules.)

B3_COMPLEX = 15    # encoded as 2 float64s.


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



# In:  time.time-style float.
# Note: Current policy is we're not taking datetimes for here. They get turned into SCHEDs by the auto, and if
#       the user wants to turn a datetime into a STAMP64 they have to do it themselves first.
def encode_stamp64(timestamp):
    if isinstance(timestamp, float):
        return struct.pack('d', timestamp)
    raise TypeError('STAMP64 only accepts floats, please use SCHED or convert yourself first')





# In: a python complex number object. Must have real and imag properties
def encode_complex(cplx):
    return struct.pack('dd',cplx.real,cplx.imag)

