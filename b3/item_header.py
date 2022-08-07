
from six import int2byte

from b3.utils import VALID_STR_TYPES, VALID_INT_TYPES, IntByteAt
from b3.type_varint import encode_uvarint, decode_uvarint


# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | has data   | null/zero  | key type   | key type   | data type  | data type  | data type  | data type  |
# |            | user-flag  |            |            |            |            |            |            |
# +------------+------------+------------+------------+------------+------------+------------+------------+

# --- Control flags ---
# +------------+------------+
# | has data   | null/zero  |
# |            | user-flag  |
# +------------+------------+
#     0   0  (0)    Codec zero-value for given data type (0, "", 0.0 etc)
#     0   1  (1)    None/NULL/nil
#     1   x  (2)    Data len present, data bytes present, null/zero is a userflag for the codecs.

# fixme: make the bool codec use the user-flag.  we WILL have to change the encode_header API a little
#        to support "NZU" (Null/Zero/User) semantics.

# --- Key types ---
# +------------+------------+
# | key type   | key type   |
# +------------+------------+
#     0   0  (0)    no key
#     0   1  (4)    UVARINT
#     1   0  (8)    UTF8 bytes
#     1   1  (c)    raw bytess


def encode_header(data_type, key=None, is_null=False, data_len=0):
    ext_data_type_bytes = len_bytes = b""
    cbyte = 0x00

    # --- Null & data len ---
    if is_null:
        cbyte |= 0x40                                    # data value is null. Note: null supercedes has-data for api purposes
    else:
        if data_len:
            cbyte |= 0x80                                # has data flag on
            len_bytes = encode_uvarint(data_len)

    # --- Key type ---
    key_type_bits, key_bytes = encode_key(key)
    cbyte |= (key_type_bits & 0x30)                      # middle 2 bits for key type

    # --- Data type ---
    if data_type > 14:
        ext_data_type_bytes = encode_uvarint(data_type)  # 'extended' data types 15 and up are a seperate uvarint
        cbyte |= 0x0f                                    # control byte data_type bits set to all 1's to signify this
    else:
        cbyte |= (data_type & 0x0f)                      # 'core' data types live in the control byte's bits only.

    # --- Build header ---
    out = [int2byte(cbyte), ext_data_type_bytes, key_bytes, len_bytes]
    return b"".join(out)


def decode_header(buf, index):
    cbyte,index = IntByteAt(buf, index)                  # control byte

    # --- data type ---
    data_type = cbyte & 0x0f
    if data_type == 15:
        data_type,index = decode_uvarint(buf, index)     # 'extended' data types 15 and up follow the control byte

    # --- Key ---
    key_type_bits = cbyte & 0x30
    key,index = decode_key(key_type_bits, buf, index)    # key bytes

    # --- Null & Data Len ---
    data_len = 0
    has_data = bool(cbyte & 0x80)
    if has_data:
        data_len, index = decode_uvarint(buf, index)     # data len bytes
        is_null = False     # for API purposes, has_data forces is_null to false
        # we may extend this later to enable the is_null bit to be used as a user flag when has_data is true.
    else:
        is_null = bool(cbyte & 0x40)

    return data_type, key, is_null, data_len, index


# Out: the key type bits, and the key bytes.

def encode_key(key):
    ktype = type(key)
    if key is None:               # this is more idiomatic python than 'NoneType' (which is gone from types module in py3)
        return 0x00, b""
    if ktype in VALID_INT_TYPES:
        return 0x10, encode_uvarint(key)
    if ktype in VALID_STR_TYPES:
        keybytes = key.encode("utf8","replace")
        return 0x20, encode_uvarint(len(keybytes)) + keybytes
    if ktype == bytes:
        return 0x30, encode_uvarint(len(key)) + key
    raise TypeError("Key type must be None, uint, str or bytes, not %s" % ktype)


# Out: the key, and the new index

def decode_key(key_type_bits, buf, index):
    if key_type_bits == 0x00:
        return None, index
    if key_type_bits == 0x10:
        return decode_uvarint(buf, index)            # note returns number, index
    if key_type_bits == 0x20:
        klen,index = decode_uvarint(buf, index)
        key_str_bytes = buf[index:index+klen]
        return key_str_bytes.decode("utf8"), index+klen
    if key_type_bits == 0x30:
        klen,index = decode_uvarint(buf, index)
        key_bytes = buf[index:index+klen]
        return key_bytes, index+klen
    raise TypeError("Invalid key type in control byte")


# Policy: we ARE doing zero-value signalling.
# Policy: data types 15 and up are encoded as a seperate uvarint immediately following the control byte,
#         and the control byte's data type bits are set to all 1 (x0f) to signify this.


