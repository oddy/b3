
# B3 data types & their id numbers
# Note: The core type numbers are all intended to fit into the lower half of the item header control byte.
# Note: NEVER have a module in your project named types.py!! Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

B3_RESERVED         = 0     # unused.                               todo: error check it?
# B3_END = 0        # This used to be a proposed end marker. Now Unused because we dont support unknown-sized items.

# --- Structure types ---
B3_COMPOSITE_DICT   = 1     # identical to COMPOSITE_LIST on the wire, hints to parser to yield a dict-like obj where possible.
B3_COMPOSITE_LIST   = 2     # identical to COMPOSITE_DICT on the wire, hints to parser to yield a list-like obj where possible

# --- Core scalar types ---
B3_BYTES            = 3     # array of bytes.                       Note: str in py2.    for bytes.
B3_UTF8             = 4     # UTF8 strings.                         for str in py3 and unicode in py2.
B3_BOOL             = 5     # True or False.                                             for bool.

B3_INT64            = 6     # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT          = 7     # unsigned varint                       slower & small/large for ints.
B3_SVARINT          = 8     # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python

B3_FLOAT64          = 9     # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL          = 10    # Arbitrary Precision decimals.         slower & compact     for decimal.

# B3_VARSTAMP       = 11    # Proposed varint unix SECONDs.         todo: do we support this??
B3_STAMP64          = 12    # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time.
                            #  (ie, timestamps gotten with now() and friends) time.time() (yr 1678-2262)

B3_SCHED            = 13    # [some sort of]LOCAL time, offset TO utc, TZname.  for user-schedule local time.
                            # (ie, times gotten from user input, appointments and schedules, future times.)

# UNUSED            = 14

# --- Extended-registry types ---
# Note: the extended-reg uses a separate uvarint in the header for the data type number (see item_header.py)

B3_RESERVED_15      = 15   # Policy: we could totally use 15, but currently not to avoid confusion with the ext-type format.
B3_COMPLEX          = 16   # encoded as 2 float64s.


DATATYPE_NAMES = {
    0 : u"<reserved 0>",
    1 : u"B3_COMPOSITE_DICT",
    2 : u"B3_COMPOSITE_LIST",
    3 : u"B3_BYTES",
    4 : u"B3_UTF8",
    5 : u"B3_BOOL",
    6 : u"B3_INT64",
    7 : u"B3_UVARINT",
    8 : u"B3_SVARINT",
    9 : u"B3_FLOAT64",
    10: u"B3_DECIMAL",
    11: u"<unused 11>",            # todo: varstamp?
    12: u"B3_STAMP64",
    13: u"B3_SCHED",
    14: u"<unused 14>",
    15: u"B3_RESERVED_15",
    16: u"B3_COMPLEX",
    }

def b3_type_name(data_type):
    return DATATYPE_NAMES.get(data_type, u"<unknown %i>" % (data_type,))
