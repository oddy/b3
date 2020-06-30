
# B3 Design & Wire Format
This document describes the B3 binary format, including data type formats, the structure of composite items, and the format of the item header. It also documents semantics and policies for the two main types of packer/encoder - schema and schemaless.
> Note: Here and in the Python code, the term _encode_ means _pack to bytes_ and vice versa for decode.

### Core drivers and policy goals
These are in rough order of priority. 
* Simplicity & Correctness -> Security
* Interoperability & Compatibility (forward & backward)
* Flexibility
* Compactness
* Performance

## Format overview
B3 is a TLV ("type-length-value") based format. All data structures are encoded on the wire as a series of **items**. Each **item** has a value, size, data type, and optional key. 

B3 is a 'bottom up' format, where all items have a known size. This means it:
* does not support "unknown size" items, [^1] 
* does support nested items - the 'inner' items must first be encoded, then included in outer items. 

### Varints
B3 uses LEB128-format variable length encoded integers in a number of places, unsigned ("**UVARINT**") and signed ("**SVARINT**"). This format ensures small numbers use few bytes. See https://en.wikipedia.org/wiki/LEB128 for more information.

## Item format
Units of data are encoded as "Items".

An item consists of a header, usually followed by the item value's encoded bytes.

The header consists of a mandatory control byte followed by some optional header components, as follows:

```text
<BYTE control> [UVARINT 15+ type#] [BYTES key] [UVARINT data length]  [BYTES data]
--------------------------- item_header ----------------------------  -- codecs --
```

### Control Byte
The control byte bits are:
```text
+------------+------------+------------+------------+------------+------------+------------+------------+
| is_null    | has_data   | key type   | key type   | data type  | data type  | data type  | data type  |
+------------+------------+------------+------------+------------+------------+------------+------------+
```

#### Is_null
If this bit is 1, the item's data value is NULL (None in Python). has_data is ignored and must be 0, and the data length and data bytes components must be absent.
If this bit is 0, then has_data is processed.

#### Has_data
If this bit is 0, then the data length and data bytes components must be absent, and the item's data value is the zero-value for it's type.

If this bit is 1, then the data length and data bytes components must be present. 

> has_data 1 and is_null 1 is an invalid state.

#### Key type
These two bits control the key component's presence and type, as follows:
```text
    0   0  no key
    0   1  integer key UVARINT encoded
    1   0  string key size in bytes UVARINT encoded, then string key encoded to UTF8 bytes
    1   1  bytes key size UVARINT encoded, then key bytes
```

#### Data type
These bits form an integer from 0-15, which is the items data type number. 

Values 0-14 correspond to the core data types documented in the Data Types section below. 

Value 15 means the actual data type number is encoded as a UVARINT immediately following the control byte.

> Data type numbers __96 through 8191__ inclusive, are open for use as User-Defined Types. All other type numbers are reserved for the use of the B3 standard.

### Key
As above (key type).

### Data length
The data length is encoded as a UVARINT. 

If the data length can be absent altogether only when is_null is 1 or has_data is 0. 
> This means no bytes are wasted if encoding NULLS or zero values for items.

### Item component structure
1. The control byte begins the item, and is always present.
2. The "15+ data type number" (if any) immediately follows (1) and is encoded as a UVARINT.
3. The key (if any) follows (1) and is encoded according to the key type bits as above.
4. The data length (if any) follows (2) and is encoded as a UVARINT.
5. The item value's data bytes follow (4).

On the wire, this looks like:
```text
<BYTE control> [UVARINT 15+ type#] [BYTES key] [UVARINT data length]  [BYTES data]
--------------------------- item_header ----------------------------  -- codecs --
```


## Composite Items
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




## Schema pack/unpack semantics

## Schemaless pack/unpack semantics. 

## Forward & Backward compatibility

## data types and their encodings.





[^1]: The only use-cases we could think of for unknown-size items were a) huge data structures like DB tables which will have their own sizing anyway, and b) streaming TCP scenarios which always end up being chunked anyway for a better UX.

