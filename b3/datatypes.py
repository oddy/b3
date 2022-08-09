


# B3 data types & their id numbers

# --- Core types ---

# bytes = 0
# utf8 = 1
# bool = 2
# uVar = 3
# sVar  = 4
# u32 = 5
# s32 = 6
# u64 = 7
# s64 = 8
# F32  9
# F64  10
# decimal  11
# sched   12
# list = 13
# dict = 14
# 15 unused
# complex = 16


# Policy: get rid of stamp64
# Policy: float32 it is, because python struct can't do any floats higher than 64 bit.

# fixme: make bool use the user-flag

B3_BYTES            = 0     # array of bytes.                       Note: str in py2.    for bytes.
B3_UTF8             = 1     # UTF8 strings.                         for str in py3 and unicode in py2.
B3_BOOL             = 2     # True or False.                                             for bool.
B3_UVARINT          = 3     # unsigned varint                       slower & small/large for ints.
B3_SVARINT          = 4     # signed varint, zigzag encoded.        slower & small/large for ints.



B3_S64              = 8     # signed 64bit integer                  faster & medium      for ints.

B3_FLOAT64          = 10    # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL          = 11    # Arbitrary Precision decimals.         slower & compact     for decimal.
B3_SCHED            = 12    # Local date-times YMDHMS & optional subsec, offset to utc, TZname, for user-input & future times.
B3_LIST             = 13    # identical to DICT on the wire, hints to parser to yield a list-like obj where possible
B3_DICT             = 14    # identical to LIST on the wire, hints to parser to yield a dict-like obj where possible.

# --- Extended types ---

# B3_RESERVED_15    = 15    # Policy: we could totally use 15, but currently not to avoid confusion with the ext-type format.
B3_COMPLEX          = 16    # encoded as 2 float64s.


# Note: The core type numbers are all intended to fit into the lower half of the item header control byte.
#       Extended type numbers are encoded in a varint following the header control byte.
# Note: NEVER have a module in your project named types.py!! Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# Policy: Numbers 96 to 8191 reserved for User-Defined Types
#         That's 1/4 of the one-byte space, and 1/2 of the two-byte space.


# --- Name reverse lookup (for friendly error messages) ---

DATATYPE_NAMES = {
    0 : u"B3_BYTES",
    1 : u"B3_UTF8",
    2 : u"B3_BOOL",
    3 : u"B3_UVARINT",
    4 : u"B3_SVARINT",
    5 : u"B3_none5",
    6 : u"B3_none6",
    7 : u"B3_none7",
    8 : u"B3_S64",
    9 : u"B3_none9",
    10: u"B3_FLOAT64",
    11: u"B3_DECIMAL",
    12: u"B3_SCHED",
    13: u"B3_LIST",
    14: u"B3_DICT",
    15: u"B3_RESERVED_15",
    16: u"B3_COMPLEX",
    }

def b3_type_name(data_type):
    return DATATYPE_NAMES.get(data_type, u"B3_UNKNOWN_TYPE_%i>" % (data_type,))
