# B3 Usage examples
# =================

from __future__ import print_function
import decimal, datetime
from pprint import pprint

import b3

# You can pack lists of things (like json.dumps):

list_data = [ None,  b"foo",  u"bar",  True,  -69,  2.318,  46j,  [1,2,3],  {4:5, 6:7},
              decimal.Decimal("13.37"), datetime.datetime.now() ]
            # Complex numbers, decimal numbers, and dates and times all work.

list_buf = b3.pack(list_data)


# You can pack dicts of things:

dict_data = { 1:1, u"2":u"2", b"3":b"3" }       # byte keys are supported as well as string and number keys

dict_buf = b3.pack(dict_data)


# You can save on slicing when unpacking by giving unpack a start index:

out_list = b3.unpack(list_buf, 0)
out_dict = b3.unpack(dict_buf, 0)

# Visual comparison-
print("\nList input:")
pprint(list_data)
print("\nList output:")
pprint(out_list)

print("\nDict matches?")
print(repr(dict_data == out_dict))


# You can make messages using a "type, name, tag_number" schema (like protobuf):
# (See datatypes.py for the available types)

SCHEMA = (
    (b3.B3_BYTES,   "bytes1",  1),
    (b3.B3_UVARINT, "number1", 2),
    )

# Schema packing/unpacking is to and from python Dicts.

sch_data = dict(bytes1=b"foo", number1=69)

sch_buf = b3.schema_pack(SCHEMA, sch_data)

# You can give the unpacker a start and end index too, to save on slicing

out_sch = b3.schema_unpack(SCHEMA, sch_buf, 0, len(sch_buf))

print("\nSchema matches?")
print(repr(sch_data == out_sch))

# Schema is intended for flat data structures, but nesting is still straightforward,
# You can pack nested fields first, building bottom-up:

OUTER_SCHEMA = (
    (b3.B3_UVARINT,         "index",         1),
    (b3.B3_UTF8,            "label",         2),
    (b3.B3_COMPOSITE_DICT,  "inner_message", 3)
    )

inner_data = dict(bytes1=b"hello", number1=1337)
inner_buf  = b3.schema_pack(SCHEMA, inner_data)
outer_data = dict(index=23, label=u"ss", inner_message=inner_buf)
outer_buf  = b3.schema_pack(OUTER_SCHEMA, outer_data)


# Unpacking is the reverse, so a little bit manual, but still easy:

ret_outer  = b3.schema_unpack(OUTER_SCHEMA, outer_buf, 0, len(outer_buf))
inner_buf  = ret_outer['inner_message']
ret_inner  = b3.schema_unpack(SCHEMA, inner_buf, 0, len(inner_buf))

print("\nNesting matches?:")
print("inner ",repr(inner_data == ret_inner))
print("outer ",repr(outer_data == ret_outer))


# schema_unpack() can unpack messages from pack() if you keep a few simple rules in mind. (use dicts!)
# This means you can start with json-like and 'upgrade' to schemas later, or have "quick-n-dirty" clients talking to schema-ed servers.
# Going the other way (schema_pack() -> unpack()) is harder but doable if you're prepared to accept tag numbers as keys instead of string names.

source_data = dict(tom=u"hello", dick=u"world", harry=777)
source_buf  = b3.pack(source_data, with_header=False)           # todo: this should still be embed=True

DEST_SCHEMA = ((b3.B3_UTF8, "tom", 1), (b3.B3_UTF8, "dick", 2), (b3.B3_SVARINT, "harry", 3))
dest_data   = b3.schema_unpack(DEST_SCHEMA, source_buf, 0, len(source_buf))

print("\nInterop matches?:")
print(repr(source_data == dest_data))




