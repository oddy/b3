
# B3 data types & codec import/lookup table

# todo: the module's actual UX
# Note: NEVER have a module in your project named types.py!! Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.
# Todo: Urgent: tidy all these number values up, because all the composite tests depend on the number values

B3_RESERVED = 0
# B3_END = 0        # This used to be a proposed end marker. Always 1 byte, always \x00. Unused because we dont support unsized items.

# --- Structure types ---
B3_COMPOSITE_DICT = 1   # same as BAG on wire, acts as hint to parser to yield a dict-like obj where possible
B3_COMPOSITE_LIST = 2   # same as BAG on wire, acts as hint to parser to yield a list-like obj where possible

# --- Scalar types ---
B3_BYTES    = 3    # array of bytes.                       Note: str in py2.    for bytes.
B3_UTF8     = 4    # UTF8 strings.                        for str in py3 and unicode in py2.
B3_BOOL     = 5    # True or False.                                             for bool.

B3_INT64    = 6    # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT  = 7    # unsigned varint                       slower & small/large for ints.
B3_SVARINT  = 8    # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python

B3_FLOAT64  = 9    # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL  = 10   # Arbitrary Precision decimals.         slower & compact     for decimal.

B3_STAMP64  = 11   # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time.
                   # (ie, timestamps gotten with now() and friends) time.time() (yr 1678-2262)
# B3_VARSTAMP = 12 # Proposed varint unix SECONDs.
B3_SCHED    = 13   # [some sort of]LOCAL time, offset TO utc, TZname.              for user-schedule local time. (ie, times gotten from user input,
                   # appointments and schedules, future times.)

B3_COMPLEX  = 14   # encoded as 2 float64s.

# Blair's idea:
# 15 = EXT_TYPE         with a varint after for the extended type numbers.

# User defined types become a range in that range.

# Actually how would these 2 different ranges be handled in code? This is probably a bad idea.
# ONE range would be ok, with a designated area for user-defined.

# two ranges = we need a flag as well as the number. bad bad bad.


# But we dont need these unless we're grabbing that item_header bit back from the zero-value stuff.
#

# Maybe eat COMPLEX into an EXT_TYPE

# --- Codec functions ---
import type_basic
import type_varint
import type_decimal
import type_sched

# If there's no codec for a type, then it's a yield-as-bytes. (for e.g. schema-composite, and the actual B3_BYTES type)
# NULL is not a specific type, it is a flag in the item header. (So any item can be NULL and also STILL have a type, on the wire)

CODECS = {
    B3_BOOL     : (type_basic.encode_bool,      type_basic.decode_bool),
    B3_UTF8     : (type_basic.encode_utf8,      type_basic.decode_utf8),
    B3_INT64    : (type_basic.encode_int64,     type_basic.decode_int64),
    B3_FLOAT64  : (type_basic.encode_float64,   type_basic.decode_float64),
    B3_STAMP64  : (type_basic.encode_stamp64,   type_basic.decode_stamp64),
    B3_COMPLEX  : (type_basic.encode_complex,   type_basic.decode_complex),
    B3_UVARINT  : (type_varint.encode_uvarint,  type_varint.codec_decode_uvarint),  # note codec-specific varint decoder function
    B3_SVARINT  : (type_varint.encode_svarint,  type_varint.codec_decode_svarint),  # note codec-specific varint decoder function
    B3_DECIMAL  : (type_decimal.encode_decimal, type_decimal.decode_decimal),
    B3_SCHED    : (type_sched.encode_sched,     type_sched.decode_sched),
}

# Policy: small-scale bottom-up-assembly data items.
# bottom-up-assmbly means the size-in-bytes of everything is always known.
# Counter-Rationale: the only use cases blair and i could think of for unknown-size items are:
# 1) Huge datastructures (e.g. qsa tables) which will have their own sizing,
# 2) e.g. tcp comms big-long-streaming which should always be chunked anyway!


