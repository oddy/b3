
# B3 Public API

__version__ = "0.9.1"

from b3.datatypes import *
from b3.composite_dynamic import pack, unpack, unpack_into
from b3.composite_schema import schema_pack, schema_unpack

__all__ = [
    u"pack", u"unpack", u"unpack_into",
    u"schema_pack", u"schema_unpack",
    u"encode_uvarint", u"decode_uvarint",

    u"B3_COMPOSITE_DICT", u"B3_COMPOSITE_LIST",
    u"B3_BYTES", u"B3_UTF8", u"B3_BOOL",
    u"B3_INT64", u"B3_UVARINT", u"B3_SVARINT",
    u"B3_FLOAT64", u"B3_DECIMAL",
    u"B3_STAMP64", u"B3_SCHED",
    u"B3_COMPLEX",
]

# B3 software Architecture:
# |Dynamic Composite encoder| ->(dict keynames)-> |Header-encoder| <-(bytes)<- |Datatype codecs|
# |Schema  Composite encoder| ->(tag numbers)  -^

# Note: In the comments throughout we use "Encode" and "Pack" terminology interchangeably. Sorry about it.

