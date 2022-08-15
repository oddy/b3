
# B3 data types & their id numbers

# --- Core types ---
B3_BYTES            = 0   # array of bytes.   Note: str in py2.    for bytes.
B3_UTF8             = 1   # UTF8 strings.     for str in py3 and unicode in py2.
B3_BOOL             = 2   # True or False.
B3_UVARINT          = 3   # unsigned varint                 (small or v.large ints)
B3_SVARINT          = 4   # signed varint, zigzag encoded.
B3_U64              = 5
B3_S64              = 6   # signed 64bit integer
B3_FLOAT64          = 7   # IEEE754 64bit signed float.
B3_DECIMAL          = 8   # Arbitrary Precision decimals.
B3_SCHED            = 9   # Datetime with tz/offset/subsec etc.  for future times.
B3_RESERVED_A       = 10
B3_RESERVED_B       = 11
B3_RESERVED_C       = 12  # (c) this may become a 'generic composite object' in future.
B3_LIST             = 13  # (d) list-like composite object
B3_DICT             = 14  # (e) dict-like composite object

# --- Extended types ---
# B3_RESERVED_15    = 15  # Policy: we could totally use 15, but currently not to avoid confusion with the ext-type format.
B3_COMPLEX          = 16  # encoded as 2 float64s.


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
    5 : u"B3_U64",
    6 : u"B3_S64",
    7 : u"B3_FLOAT64",
    8 : u"B3_DECIMAL",
    9 : u"B3_SCHED",

    13: u"B3_LIST",
    14: u"B3_DICT",
    15: u"B3_RESERVED_15",
    16: u"B3_COMPLEX",
}

def b3_type_name(data_type):
    return DATATYPE_NAMES.get(data_type, u"B3_UNKNOWN_TYPE_%i>" % (data_type,))
