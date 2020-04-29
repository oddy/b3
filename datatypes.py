import struct, decimal
#from six import PY2\
import six
from   six import int2byte
from datetime import datetime

from varint import encode_uvarint

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

B3_STAMP64  = 13   # Signed 64bit unix ns, no TZ           faster & medium      for datetime. (yr 1678-2262) (yields to time.time on python if using automode)
B3_SCHED    = 14   # Arb Prec unix sec, opt ns,offset,TZ.  slower & small/large for datetime.                (yields to

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



# All these Out bytes.

# i say we DONT take floats if it's too hard to convert them / get the info we need out of them
# / have to get precision out of them.

# In: num - a float/double or decimal.Decimal type
def encode_decimal(num):
    if not isinstance(num, decimal.Decimal):
        raise TypeError("only accepts decimal.Decimal objects")

    # Top 4bits:
    # bit 4 (0x80) : 0=number, 1=special
    # bit 3 (0x40) : 0=+ve number, 1=-ve number
    # bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo   [special] 0=nan 1=infinity
    # bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows  [special] 0=qnan 1=snan

    # Bottom 4bits:
    # [number]  exponent if top bit1=0, unused otherwise
    # [special] unused.

    sign,digits,exp = num.as_tuple()
    special   = not num.is_finite()

    # --- Control bits & special values (inf, nan) ---
    bits = 0x00
    if special:                                     # bit 4 (0x80) : 0=number, 1=special
        bits |= 0x80

    if sign:                                        # bit 3 (0x40) : 0=+ve number, 1=-ve number
        bits |= 0x40

    if special:                                     # bit 2 (0x20) : [special] 0=nan 1=infinity
        if num.is_infinite():
            bits |= 0x20
    else:                                           # bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo
        if exp < 0:
            bits |= 0x20

    if special:                                     # bit 1 (0x10) : [special] 0=qnan 1=snan
        if num.is_snan():
            bits |= 0x10
        return int2byte(bits)                       # *** Special only, we're done ***

    # --- Exponent ---
    exp_abs   = abs(exp)

    if exp_abs > 0x0f:                              # bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows
        bits |= 0x10                                # exponent > 15, store it in varint
        out = [int2byte(bits), encode_uvarint(exp_abs)]      # uv b/c exp sign already done & we're trying to be compact
    else:                                           # exponent =< 15, store it in low nibble
        bits |= (exp_abs & 0x0f)
        out = [int2byte(bits)]

    # --- Significand ---
    if digits:
        signif = int(''.join(map(str, digits)))     # [screaming intensifies]
        if signif:                                  # Note that 0 = no signif bytes at all.
            out.append(encode_uvarint(signif))

    return b''.join(out)



# do math using decimal context or 'normal' float math, depending on what comes in.

# In:  time.time-style float.
# Note: Current policy is we're not taking datetimes for here. They get turned into SCHEDs by the auto, and if
#       the user wants to turn a datetime into a STAMP64 they have to do it themselves first.
def encode_stamp64(timestamp):
    if isinstance(timestamp, float):
        return struct.pack('d', timestamp)
    raise TypeError('STAMP64 only accepts floats, please use SCHED or convert yourself first')


# In: datetime.  maybe a time.time-style float, but probably not.
def encode_sched(datetime):         # this one might need its own file
    return b'\x69'

# In: a python complex number object. Must have real and imag properties
def encode_complex(cplx):
    return struct.pack('dd',cplx.real,cplx.imag)

