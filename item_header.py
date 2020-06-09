
from   six import PY2, int2byte, byte2int

from utils import VALID_STR_TYPES, VALID_INT_TYPES, IntByteAt
from type_varint import encode_uvarint, encode_svarint, decode_svarint, decode_uvarint

# --- item structure ---
# [header BYTE] [key (see below)] [data len UVARINT] [data BYTES]
# \------------------------------------------------/                            = handled here

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | key type   | key type   | not-null   | data type? | data type  | data type  | data type  | data type  |
# +------------+------------+------------+------------+------------+------------+------------+------------+


# --- Key bits   &   structure ---
#     0   0  (0)     no bytes
#     0   1  (4)     UVARINT
#     1   0  (8)     UTF8 bytes
#     1   1  (c)     raw bytess


# Policy:  Everything has a size, except B3_END.  If we want B3_END to be 0x00 then the null flag has to be inverted.
# Policy:  So now its a none-null flag. But only for the wire format, the rest of the code uses is_null so we flip it.
# Todo:    size of 0 = the zero-value for the type. Do this (much) later.

# We might need a flag for unknown size!
# OR make sizes an svarint and use -1 to represent unknown size

def encode_header(data_type, key, data_len=0, is_null=False):
    key_type_bits, key_bytes = encode_key(key)
    cbyte = 0x00
    cbyte |= key_type_bits & 0xc0                      # top 2 bits key type
    cbyte |= data_type     & 0x1f                      # bottom 5 bits data type
    if not is_null:
        cbyte |= 0x20                                  # 3rd bit 0=is null, 1 = NOT null
    out = [int2byte(cbyte), key_bytes]
    if not is_null:
        out.append(encode_svarint(data_len))           # data len bytes
    return b"".join(out)


def decode_header(buf, index):
    cbyte,index = IntByteAt(buf, index)                # control byte
    key,index = decode_key(cbyte & 0xc0, buf, index)   # key bytes
    is_null = not bool(cbyte & 0x20)
    if not is_null:
        data_len,index = decode_svarint(buf, index)    # data len bytes
    else:
        data_len = 0
    data_type = cbyte & 0x1f
    return key, data_type, data_len, is_null, index    # but not the data bytes themselves, because the decoders nom them.


# Out: the key type bits, and the key bytes.

def encode_key(key):
    ktype = type(key)
    if key is None:               # this is more idiomatic python than 'NoneType' (which is gone from types module in py3)
        return 0x00, b""
    if ktype in VALID_INT_TYPES:
        return 0x40, encode_uvarint(key)
    if ktype in VALID_STR_TYPES:
        keybytes = key.encode("utf8","replace")
        return 0x80, encode_uvarint(len(keybytes)) + keybytes
    if ktype == bytes:
        return 0xc0, encode_uvarint(len(key)) + key
    raise TypeError("Key type must be None, int, str or bytes, not %s" % ktype)


# Out: the key, and the new index

def decode_key(key_type_bits, buf, index):
    if key_type_bits == 0x00:
        return None, index
    if key_type_bits == 0x40:
        return decode_uvarint(buf, index)            # note returns number, index
    if key_type_bits == 0x80:
        klen,index = decode_uvarint(buf, index)
        key_str_bytes = buf[index:index+klen]
        return key_str_bytes.decode("utf8"), index+klen
    if key_type_bits == 0xc0:
        klen,index = decode_uvarint(buf, index)
        key_bytes = buf[index:index+klen]
        return key_bytes, index+klen
    raise TypeError("Invalid key type in control byte")


# Note: discussion about size bits and zero bits and funky stuff like that
# Size bit keeps us future proof! WHILE enabling the option of some types having no size!
# Currently the only types that have no size are None and B3_END
# (Actually if we have a size bit, we can have a whole different registry of unsized types!  This is more complex tho.)
# if we can make 'true type' and 'false type' work in code without it being really shit, then give that a go.

