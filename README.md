

# B3 = Better Binary Buffers

B3 is a data serializer, it packs data structures to bytes & vice versa. It has:
* The schema power of protobuf, without the setup/compiler pain,
* The quick-start ease of json.dumps, but with support for datetimes,
* The compactness of msgpack, but without a large zoo of data types. 

With B3 you can fast-start with schema-less data (like json), and move to schemas (like protobuf) later & stay compatible. Or have ad-hoc json-like clients talk to rigorous protobuf-like servers without pain & suffering.

The small number of lovingly-handcrafted data types means often the only choice you need make is between Fast or Compact.

This version is pure python, no dependencies apart from Six (and pytest for the tests).
Tested working in python 3.8 & 2.7 on windows & linux.

## Version

B3 is now version 1.x, it is out of beta.

__The wire format and existing core data types are now *frozen* and *will not change*.__

* Except for the unused core types 10,11,12 which may have a type assigned in future, and
* Except for SCHEDs unfinished named-timezone support, which needs py3.10+)

(v1.x is not backward compatible with beta 0.9.x versions) 

## Installing

```
pip install b3buf

>>> import b3
```

### Getting Started

You can pack lists of things (like json.dumps):

```
import b3
list_data = [ None,  b"foo",  u"bar",  True,  -69,  2.318,  46j,  [1,2,3],  {4:5, 6:7},
              decimal.Decimal("13.37"), datetime.datetime.now() ]

list_buf = b3.pack(list_data)

out_list = b3.unpack(list_buf)
```
Complex numbers, decimal numbers, and dates and times all work.

You can pack dicts of things:

```
dict_data = { 1:1, u"2":u"2", b"3":b"3" }

dict_buf = b3.pack(dict_data)

out_dict = b3.unpack(dict_buf, 0)
```
Byte keys are supported as well as string and number keys

You can save on slicing when unpacking by giving unpack a start index


### Schema Packing
You can make messages using a "type, name, tag_number" schema (like protobuf)

```
SCHEMA = (
    (b3.B3_BYTES,   "bytes1",  1),
    (b3.B3_UVARINT, "number1", 2),
    )
```

Schema packing/unpacking is to and from python Dicts.
```
sch_data = dict(bytes1=b"foo", number1=69)

sch_buf = b3.schema_pack(SCHEMA, sch_data)

out_sch = b3.schema_unpack(SCHEMA, sch_buf)
```


## Tests

B3 ships with an extensive test suite, using pytest. 

```
pip install pytest
cd /your/site-packages/b3
pytest 
```

## More Info

See the tests, and examples.py in the tests folder for more examples (including how to nest schemas)

See datatypes.py for the available data types.

See wire_format.md for an overview of the wire format.


## Licensing

The code in this project is licensed under MIT license. See LICENSE.txt.