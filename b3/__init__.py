# B3 Public API

__version__ = "1.0.9"

from b3.datatypes import *
from b3.composite_dynamic import pack, unpack, unpack_into
from b3.composite_schema import schema_pack, schema_unpack
from b3.type_varint import encode_uvarint, decode_uvarint
from b3.item import encode_item, encode_item_joined, decode_header, decode_value

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
    "BYTES",
    "UTF8",
    "BOOL",
    "UVARINT",
    "SVARINT",
    "U64",
    "S64",
    "FLOAT64",
    "DECIMAL",
    "SCHED",
    "DICT",
    "LIST",
    "COMPLEX",
]

# B3 software Architecture:
# |Dynamic Composite encoder| ->(dict keynames)-> |Header-encoder| <-(bytes)<- |Datatype codecs|
# |Schema  Composite encoder| ->(tag numbers)  -^

# Note: In the comments throughout we use "Encode" and "Pack" terminology interchangeably. Sorry about it.
