
# B3 Design & Wire Format
This document describes the B3 binary format, including data type formats, the structure of composite items, and the format of the item header. It also documents semantics and policies for the two main types of packer/encoder - schema and schemaless.
> Note: Here and in the Python code, the term _encode_ means _pack to bytes_ and vice versa for decode.

### Core drivers and policy goals
These are in rough order of priority. 
* Simplicity & Correctness -> Security
* Interoperability & Compatibility (forward & backward)
* Easy to install and use (no 3rd party libraries)
* Flexibility
* Compactness
* Performance

# Format overview
B3 is a TLV ("type-length-value") based format. All data structures are encoded on the wire as a series of **items**. Each **item** has a value, size, data type, and optional key. 

B3 is a 'bottom up' format, where all items have a known size. This means it:
* does not support "unknown size" items, [^1] 
* does support nested items - the 'inner' items must first be encoded, then included in outer items. 

### Varints
B3 uses LEB128-format variable length encoded integers in a number of places, unsigned ("**UVARINT**") and signed ("**SVARINT**"). This format ensures small numbers use few bytes. See https://en.wikipedia.org/wiki/LEB128 for more information.

# Item format
Units of data are encoded as "Items".

An item consists of a mandatory control byte, followed by some optional header components, followed by the item value's encoded bytes, as follows:

### Item component structure
1. The **control byte** begins the item, and is always present.
2. The **data type number** (if any) immediately follows (1) and is encoded as a UVARINT.
3. The **key** (if any) follows (2) and is encoded as described below.
4. The **data length** (if any) follows (2) and is encoded as a UVARINT.
5. The item **value**'s data bytes follow (4).

On the wire, this looks like:
```text
<BYTE control> [UVARINT type] [BYTES key] [UVARINT data length]  [BYTES data]
------------------------ item_header --------------------------  -- codecs --
```

### Control Byte
The control byte dictates the presence/absence of item components, and also holds the data type number for types 0-15.
It's bits are as follows:
```text
+------------+------------+------------+------------+------------+------------+------------+------------+
| data type  | data type  | data type  | data type  |  has data  | null/zero  | key type   | key type   |
+------------+------------+------------+------------+------------+------------+------------+------------+
```

### Data type
The upper 4 bits of the control byte form an integer from 0-15, which is the item's data type number.

Values 0-14 correspond to the core data types documented in the Data Types section below. 

Value 15 means the actual data type number is encoded as a UVARINT immediately following the control byte.

> Data type numbers __96 through 8191__ inclusive, are open for use as User-Defined Types. All other type numbers are reserved for the use of the B3 standard.

### Key
There are 4 possible types of key:
1. No key is present at all (no key bytes follow the control byte)
2. Integer key - UVARINT encoded
3. String key - UTF8 encoded, with the UTF8 size in bytes first, UVARINT encoded.
4. Bytes key - the raw bytes, with the byte size first, UVARINT encoded.

Control byte 'key type' bits select which is present, as follows:
```text
    0   0  no key
    0   1  integer key 
    1   0  string key
    1   1  bytes key
```


### Control byte Has_data bit
*If this bit is 0,* 
* The item's data value is **either Null, or the zero-value for it's type**.
* The null/zero bit controls whether the value is Null or the zero-value.
* There are no data length bytes
* There are no data bytes

*If this bit is 1,* 
* the data length must be present, 
* the data bytes must be present. 
* The null/zero bit is not used by the header and is free for use by the data codecs.
* (Special case: the BOOL datatype uses the null/zero bit to hold it's value, so for BOOL there are no data bytes or length even through this bit is 1.)


### Control byte Is_null bit
*if has_data is 0*
* if this bit is 0,
  * item value is the zero-value for it's data type (0, empty string, etc)
* if this bit is 1,
  * item value is NULL (None, nil, etc)

*if has_data is 1*
* This bit's value is not defined by the header and is free for use by the data type codecs
* data type BOOL uses this bit to carry it's True/False value


### Data length
The data length is encoded as a UVARINT. 

Data length will be present when has_data = 1 and not present otherwise.  
> This means no bytes are wasted if encoding NULLS or zero values for items.


### Bool is special
BOOL uses the is_null bit to carry it's true/false value.

BOOL is the *only* data type for which there is no data length and no data payload bytes, even though has_data is 1.

All other data types must adhere to the "has_data controls length & payload presence" rule.


# Composite Items
Lists (arrays) and Dicts (maps) are easily supported simply by using a series of items. More exotic datastructures can be created by using a combination of keys and nesting, as follows.

### Lists
A list is encoded as a series of items on the wire, ordered by their wire order. Keys are typically not used when working with lists.

### Dicts
A dict is also encoded as a series of items on the wire. Item keys are required.

### Nested (multi level) data structures
An item's data bytes _can themselves be_ a series of encoded items, which is how nesting is achieved on a linear wire, as shown here:
```text
 --item--  --item--  ----------item----------  --item--  --item--
[hdr|data][hdr|data][hdr|--------data--------][hdr|data][hdr|data] etc
                         [hdr|data][hdr|data]
                          --item--  --item--
```


# Data types and encodings
The core data types are as follows. 
Unknown data types can be interpreted as BYTES and passed through successfully, as the length is always known and explicit.

| Name       | Number | Info                                                    |
|------------|--------|---------------------------------------------------------|
| B3_BYTES   | 0      | array of bytes.   Note: str in py2.    for bytes.       |
| B3_UTF8    | 1      | UTF8 strings.     for str in py3 and unicode in py2.    |
| B3_BOOL    | 2      | True or False.                                          |
| B3_UVARINT | 3      | unsigned varint                 (small or v.large ints) |
| B3_SVARINT | 4      | signed varint, zigzag encoded.                          |
| B3_U64     | 5      | unsigned 64bit integer                                  |
| B3_S64     | 6      | signed 64bit integer                                    |
| B3_FLOAT64 | 7      | IEEE754 64bit signed float.                             |
| B3_DECIMAL | 8      | Arbitrary Precision decimals.                           |
| B3_SCHED   | 9      | Datetime with tz/offset/subsec etc.  for future times.  |
|            | 10     | reserved for future use                                 |
|            | 11     | reserved for future use                                 |
|            | 12     | reserved for future use                                 |
| B3_LIST    | 13     | (d) list-like composite object                          |
| B3_DICT    | 14     | (e) dict-like composite object                          |
|            | 15     | reserved                                                |
| B3_COMPLEX | 16     | encoded as 3 float64s                                   |


[^1]: The only use-cases we could think of for unknown-size items were a) huge data structures like DB tables which will have their own sizing anyway, and b) streaming TCP scenarios which always end up being chunked anyway for a better UX.

