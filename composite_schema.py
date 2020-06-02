
from type_basic import *
from item_header import encode_header, decode_header

# Schema-style composite types. (as opposed to json-style composite types)
# * Single level only, nonbasic types get surfaced as bytes. Caller must then call one of our APIs to unpack them in turn.
#   - yes this involves a buffer copy.


# In: schema - tuple of (type, name, number) tuples,   data - dict

def encode_schema_comp(schema, data):
    if not isinstance(data, dict):
        raise TypeError("currently only dict input data supported by encode_schema_comp")
    return


