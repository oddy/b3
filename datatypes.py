
# B3 data types & codec import/lookup table

# todo: the module's actual UX

# Note: NEVER have a module in your project named types.py!! Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# --- Bag end marker ---
# B3_END = 0        # end marker. Always 1 byte, always \x00   # unused currently because not supporting unknown-size items.

# --- Structure types ---
B3_BAG = 1        # Our single multipurpose composite type, structured: [item][item] # (not)[B3_END]
B3_BAG_LIST = 2   # same as BAG on wire, acts as hint to parser to yield a list-like obj where possible
B3_BAG_DICT = 3   # same as BAG on wire, acts as hint to parser to yield a dict-like obj where possible

# --- datum types ---
B3_BOOL     = 5    # True or False.                                             for bool.
B3_BYTES    = 6    # List of bytes (bytearray?).           Note: str in py2.    for bytes.
B3_UTF8     = 7    # UTF8 byte strings.                    for str in py3 and unicode in py2.

B3_INT64    = 8    # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT  = 9    # unsigned varint                       slower & small/large for ints.
B3_SVARINT  = 10   # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python

B3_FLOAT64  = 12   # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL  = 11   # Arbitrary Precision decimals.         slower & compact     for decimal.

B3_STAMP64  = 13   # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time. (ie, timestamps gotten with now() and friends) time.time() (yr 1678-2262)
B3_SCHED    = 14   # [some sort of]LOCAL time, offset TO utc, TZname.              for user-schedule local time. (ie, times gotten from user input, appointments and schedules.)

B3_COMPLEX  = 15   # encoded as 2 float64s.


# Policy: the decoders don't need to return an updated index any more because everything is sized, and
# Policy: both composite decoders ignore it anyway.

# --- Codec functions ---
import type_basic
import type_varint
import type_decimal
import type_sched

# If there's no codec for a type, then its a yield-as-bytes type. (for e.g. schema-composite)
CODECS = {
    B3_BOOL     : (type_basic.encode_bool,      type_basic.decode_bool),
    B3_UTF8     : (type_basic.encode_utf8,      type_basic.decode_utf8),
    B3_INT64    : (type_basic.encode_int64,     type_basic.decode_int64),
    B3_FLOAT64  : (type_basic.encode_float64,   type_basic.decode_float64),
    B3_STAMP64  : (type_basic.encode_stamp64,   type_basic.decode_stamp64),
    B3_COMPLEX  : (type_basic.encode_complex,   type_basic.decode_complex),
    B3_UVARINT  : (type_varint.encode_uvarint,  type_varint.decode_uvarint),
    B3_SVARINT  : (type_varint.encode_svarint,  type_varint.codec_decode_svarint),  # note codec-specific decoder function here
    B3_DECIMAL  : (type_decimal.encode_decimal, type_decimal.decode_decimal),
    B3_SCHED    : (type_sched.encode_sched,     type_sched.decode_sched),
}


# We are using end-pointer params everwhere instead because everything is sized and we always build bottom-up ANYWAY.
# Rationale - the only use cases blair and i could think of for sizeless are:
# 1) Huge datastructures (e.g. qsa tables) which will have their own sizing,
# 2) e.g. sockets big-long-streaming which will always be chunked anyway!


