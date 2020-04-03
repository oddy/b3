
from six import PY2
from datetime import datetime

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
B3_VARINT   = 8    # signed varint, zigzag encoded.        slower & small/large for ints.
B3_UVARINT  = 9    # unsigned varint                       slower & small/large for ints.

B3_FLOAT64  = 10   # IEEE754 64bit signed float.           faster & medium      for floats.
B3_BIGDEC   = 11   # Arbitrary Precision decimals.         slower & small/large for floats.

B3_STAMP64  = 12   # Signed 64bit unix ns, no TZ           faster & medium      for datetime. (yr 1678-2262)
B3_SCHED    = 13   # Arb Prec unix sec, opt ns,offset,TZ.  slower & small/large for datetime.



# in: some object
# out: type code or NotImplementedError

def GuessType(obj):
    if obj is None:
        return B3_NULL

    if obj in [True, False]:
        return B3_BOOL

    if isinstance(obj, bytes):                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.
        return B3_BYTES

    if PY2 and isinstance(obj, unicode):        # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):                    # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    # todo: optimal selection for the types below here, depending on value


    # todo: selecting optimal B3 type from integer value
    if isinstance(obj, int):                    # py2: 32bit,  py3: arb prec
        if obj >= 0:    return B3_UVARINT
        else:           return B3_VARINT
        # return B3_INT64

    # todo: selecting optimal B3 type from integer value
    if PY2 and isinstance(obj, long):           # py2 arb prec
        return B3_VARINT                        # the zigzag size diff is only noticeable with small numbers.

    # todo: selection logic,  decimal library support
    if isinstance(obj, float):
        return B3_FLOAT64
        # return B3_BIGDEC

    if isinstance(obj, datetime):
        return B3_SCHED
        # return B3_STAMP64




    raise NotImplementedError('Unknown type %r' % type(obj))

# todo: do we want to support python's complex number type?



def PackBasicType(itm):
    if isinstance(itm, bytes):                  # pass through.
        return TYPE_BYTES, itm                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.

    if PY2 and isinstance(itm, unicode):
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, str):                    # Py3 unicode str only, py2 done by the bytes check above.
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, int):
        return TYPE_VARINT, encode_varint(itm)

    # ... Moar Types ...
    if isinstance(itm, (list, dict)):   raise TypeError('Pack does not accept composite types, please use one of the composite APIs')
    raise NotImplementedError('PackBasicType Unknown type %r' % type(itm))

