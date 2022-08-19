# B3 data types & their id numbers

# --- Core types ---
BYTES       = 0   # array of bytes.   Note: str in py2.    for bytes.
UTF8        = 1   # UTF8 strings.     for str in py3 and unicode in py2.
BOOL        = 2   # True or False.
UVARINT     = 3   # unsigned varint                 (small or v.large ints)
SVARINT     = 4   # signed varint, zigzag encoded.
U64         = 5   # unsigned 64bit integer
S64         = 6   # signed 64bit integer
FLOAT64     = 7   # IEEE754 64bit signed float.
DECIMAL     = 8   # Arbitrary Precision decimals.
SCHED       = 9   # Datetime with tz/offset/subsec etc.  for future times.
#                 # 10/11/12 reserved for future use
LIST        = 13  # (d) list-like composite object
DICT        = 14  # (e) dict-like composite object

# --- Extended types ---
# RESERVED15 = 15    # Policy: we could totally use 15, but currently not to avoid confusion with the ext-type format.
COMPLEX     = 16  # encoded as 2 float64s.


# Note: The core type numbers are all intended to fit into the upper half of the item header control byte.
#       Extended type numbers are encoded in a varint following the header control byte.
# Note: NEVER have a module in your project named types.py!! Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# Policy: Numbers 96 to 8191 reserved for User-Defined Types
#         That's 1/4 of the one-byte space, and 1/2 of the two-byte space.


# --- Name reverse lookup (for friendly error messages) ---

DATATYPE_NAMES = {
    0: "BYTES",
    1: "UTF8",
    2: "BOOL",
    3: "UVARINT",
    4: "SVARINT",
    5: "U64",
    6: "S64",
    7: "FLOAT64",
    8: "DECIMAL",
    9: "SCHED",
    13: "LIST",
    14: "DICT",
    15: "B3_RESERVED_15",
    16: "COMPLEX",
}


def b3_type_name(data_type):
    return DATATYPE_NAMES.get(data_type, "B3_UNKNOWN_TYPE_%i>" % (data_type,))
