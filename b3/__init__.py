# B3 Public API

__version__ = "1.0.1"

from b3.datatypes import *
from b3.composite_dynamic import pack, unpack, unpack_into
from b3.composite_schema import schema_pack, schema_unpack
from b3.type_varint import encode_uvarint, decode_uvarint
from b3.item import encode_item, encode_item_joined

__all__ = [
    "pack",
    "unpack",
    "unpack_into",
    "schema_pack",
    "schema_unpack",
    "encode_uvarint",
    "decode_uvarint",
    "encode_item",
    "encode_item_joined",
    "B3_BYTES",
    "B3_UTF8",
    "B3_BOOL",
    "B3_UVARINT",
    "B3_SVARINT",
    "B3_U64",
    "B3_S64",
    "B3_FLOAT64",
    "B3_DECIMAL",
    "B3_SCHED",
    "B3_DICT",
    "B3_LIST",
    "B3_COMPLEX",
]

# B3 software Architecture:
# |Dynamic Composite encoder| ->(dict keynames)-> |Header-encoder| <-(bytes)<- |Datatype codecs|
# |Schema  Composite encoder| ->(tag numbers)  -^

# Note: In the comments throughout we use "Encode" and "Pack" terminology interchangeably. Sorry about it.
