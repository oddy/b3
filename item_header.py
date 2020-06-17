
from   six import PY2, int2byte, byte2int

from utils import VALID_STR_TYPES, VALID_INT_TYPES, IntByteAt
from type_varint import encode_uvarint, decode_uvarint

# Policy: we are NOT doing unknown sizes. Which means no B3_END.
# Policy: we are no longer inverting the null bit.
# Policy: we ARE doing zero-value signalling.
# Policy: data types 15 and up are encoded as a seperate uvarint immediately following the control byte,
#         and the control byte's data type bits are set to all 1 (x0f) to signify this.

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | is null    | has data   | key type   | key type   | data type  | data type  | data type  | data type  |
# +------------+------------+------------+------------+------------+------------+------------+------------+

# +------------+------------+
# | is null    | has data   |
# +------------+------------+
#     1   x  (2)    Value is None/NULL/nil - data len & has data ignored
#     0   0  (0)    Codec zero-value for given data type (0, "", 0.0 etc)
#     0   1  (1)    Data len present, followed by codec'ed data bytes

# +------------+------------+
# | key type   | key type   |
# +------------+------------+
#     0   0  (0)    no bytes
#     0   1  (4)    UVARINT
#     1   0  (8)    UTF8 bytes
#     1   1  (c)    raw bytess


def encode_header(data_type, key, data_len=0, is_null=False):
    ext_type_bytes = len_bytes = b""
    cbyte = 0x00

    # --- Null & data len ---
    if is_null:
        cbyte |= 0x80                                   # data value is null. Note: null supercedes has-data
    else:
        if data_len:
            cbyte |= 0x40                               # has data flag on
            len_bytes = encode_uvarint(data_len)

    # --- Key type ---
    key_type_bits, key_bytes = encode_key(key)
    cbyte |= (key_type_bits & 0x30)                     # middle 2 bits for key type

    # --- Data type ---
    if data_type > 14:
        ext_type_bytes = encode_uvarint(data_type)      # 'extended' data types 15 and up are a seperate uvarint
        cbyte |= 0x0f                                   # control byte data_typeck bits set to all 1's to signify this
    else:
        cbyte |= (data_type & 0x0f)                     # 'core' data types live in the control byte's bits only.

    # --- Build header ---
    out = [int2byte(cbyte), ext_type_bytes, key_bytes, len_bytes]
    return b"".join(out)


def decode_header(buf, index):
    cbyte,index = IntByteAt(buf, index)                # control byte
    key,index = decode_key(cbyte & 0xc0, buf, index)   # key bytes
    is_null = bool(cbyte & 0x20)
    if not is_null:
        data_len,index = decode_uvarint(buf, index)    # data len bytes
    else:
        data_len = 0
    data_type = cbyte & 0x1f
    return key, data_type, is_null, data_len, index


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

