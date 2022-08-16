from six import int2byte

from b3.utils import VALID_STR_TYPES, VALID_INT_TYPES, IntByteAt
from b3.type_varint import encode_uvarint, decode_uvarint
from b3.datatypes import B3_BOOL, B3_U64, B3_S64
from b3.type_codecs import ENCODERS, DECODERS, ZERO_VALUE_TABLE
from b3.type_basic import encode_ints, decode_ints

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | data type  | data type  | data type  | data type  |  has data  |null/zero/UF| key type   | key type   |
# +------------+------------+------------+------------+------------+------------+------------+------------+

# Note: UF = User Flag, can be used by codecs (e.g. bool) when has_data is True.

# The "5 kinds of data" and how the flags work for each:
# None              has_data false  null true
# Zero              has_data false  null false
# Bool              has_data true   null --value--
# Encoded-Data      has_data true   null n/a
# Bytes             has_data true   null n/a


# --- Control flags ---
# +------------+------------+
# | has data   |null/zero/UF|
# +------------+------------+
#     0   0  (0)    No data, value is Codec zero-value for given data type (0, "", 0.0 etc)
#     0   1  (1)    No data, value is None / NULL / nil
#     1   x  (2)    Data present (len and value), UF bit can be used by codecs such as Bool.

# Has-data==True does two things:
# 1) switches nullzero/UF into UF mode and out of null-or-zero mode - [always]
# 2) signals that a data len follows - [IFF the data type is not bool]


# --- Key types ---
# +------------+------------+
# | key type   | key type   |
# +------------+------------+
#     0   0  (0)    no key
#     0   1  (4)    UVARINT
#     1   0  (8)    UTF8 bytes
#     1   1  (c)    raw bytess


# Note: Header encoding and data encoding are done in one step here.
#       BUT header decoding and data decoding are split, because Dynamic's recursive unpack needs it.

# we can: field_bytes, is_null = SpecialEncoderFn(value) in future if wanted.
# Policy: if the data type doesn't have a codec, it should be bytes-able.


def encode_item(key, data_type, value):
    value_bytes = b""
    has_data = True
    is_null = False

    # ======= Control flags and value bytes =======
    # Note that the order of these matters. Null supercedes zero, etc etc.
    if value is None:  # null value
        # print("   ---> none path")
        has_data = False
        is_null = True

    elif data_type == B3_BOOL:  # bool type
        # print("   ---> bool path")
        is_null = value  # repurposes the null/zero flag to store its value

    elif data_type in ZERO_VALUE_TABLE and value == ZERO_VALUE_TABLE[data_type]:
        # print("   ---> zero value path")
        has_data = False

    elif B3_U64 <= data_type <= B3_S64:  # int types have a common function
        value_bytes = encode_ints(data_type, value)

    elif data_type in ENCODERS:  # codec-able value
        # print("   ---> codec path")
        EncoderFn = ENCODERS[data_type]
        value_bytes = EncoderFn(value)

    else:  # bytes value (bytes, dict, list, unknown data types)
        # print("   ---> bytes path")
        value_bytes = bytes(value)

    # ======= Header encoding =======
    ext_data_type_bytes = len_bytes = b""
    cbyte = 0x00

    # --- Null, data & data len ---
    if has_data:
        cbyte |= 0x08
    if is_null:
        cbyte |= 0x04
    if has_data and data_type is not B3_BOOL:  # has_data controls if there is a data length
        len_bytes = encode_uvarint(len(value_bytes))
        # ^^ (except for BOOL where there is never a data length)

    # --- Key type ---
    key_type_bits, key_bytes = encode_key(key)
    cbyte |= key_type_bits & 0x03  # middle 2 bits for key type

    # --- Data type ---
    if data_type > 14:
        ext_data_type_bytes = encode_uvarint(data_type)
        # ^^ 'extended' data types 15 and up are a seperate uvarint
        cbyte |= 0xF0  # control byte data_type bits set to all 1's to signify this
    else:
        cbyte |= (data_type << 4) & 0xF0  # 'core' data types live in the control byte's bits only.

    # --- Build header ---
    header_bytes = b"".join([int2byte(cbyte), ext_data_type_bytes, key_bytes, len_bytes])
    return header_bytes, value_bytes


# used for testing
def encode_item_joined(key, data_type, value):
    return b"".join(encode_item(key, data_type, value))


# Note: Header encoding and data encoding are done in one step here.
#       BUT header decoding and data decoding are split, because Dynamic's recursive unpack needs it.


def decode_header(buf, index):
    cbyte, index = IntByteAt(buf, index)  # control byte

    # --- Data type ---
    data_type = (cbyte & 0xF0) >> 4
    if data_type == 15:  # 'extended' data types 15 and up follow the control byte
        data_type, index = decode_uvarint(buf, index)

    # --- Key ---
    key_type_bits = cbyte & 0x03
    key, index = decode_key(key_type_bits, buf, index)  # key bytes

    # --- Flags ---
    data_len = 0
    has_data = bool(cbyte & 0x08)
    is_null = bool(cbyte & 0x04)

    # --- Data length ---
    if has_data and data_type != B3_BOOL:
        data_len, index = decode_uvarint(buf, index)  # data len bytes

    return key, data_type, has_data, is_null, data_len, index


def decode_value(data_type, has_data, is_null, data_len, buf, index):
    # Note: the order of these matters, be careful about changing it.
    # --- No data: Null or Zero ---
    if not has_data:
        if is_null:
            return None
        else:
            return ZERO_VALUE_TABLE.get(data_type, b"")

    # --- Data: Bool is special, its "data" is the is_null bit ---
    if data_type == B3_BOOL:
        return bool(is_null)

    # --- fixed-value integers ---
    if B3_U64 <= data_type <= B3_S64:
        return decode_ints(data_type, buf, index, index + data_len)

    # --- Encoded data ---
    if data_type in DECODERS:
        DecoderFn = DECODERS[data_type]
        return DecoderFn(buf, index, index + data_len)

    # --- Bytes (bytes, dict, list, unknown etc) ---
    else:
        return buf[index : index + data_len]


# used mainly by tests, for convenient inverse of encode_item()
def decode_item(buf, index):
    key, data_type, has_data, is_null, data_len, index = decode_header(buf, index)
    value = decode_value(data_type, has_data, is_null, data_len, buf, index)
    return key, value, index + data_len


# Convenience function, used by tests
def decode_item_type_value(buf):
    _, data_type, has_data, is_null, data_len, index = decode_header(buf, 0)
    value = decode_value(data_type, has_data, is_null, data_len, buf, index)
    return data_type, value


# Out: the key type bits, and the key bytes.


def encode_key(key):
    ktype = type(key)
    if key is None:
        return 0x00, b""
    if ktype in VALID_INT_TYPES:
        return 0x01, encode_uvarint(key)
    if ktype in VALID_STR_TYPES:
        keybytes = key.encode("utf8", "replace")
        return 0x02, encode_uvarint(len(keybytes)) + keybytes
    if ktype == bytes:
        return 0x03, encode_uvarint(len(key)) + key
    raise TypeError("Key type must be None, uint, str or bytes, not %s" % ktype)


# Out: the key, and the new index


def decode_key(key_type_bits, buf, index):
    if key_type_bits == 0x00:
        return None, index
    if key_type_bits == 0x01:
        return decode_uvarint(buf, index)  # note returns number, index
    if key_type_bits == 0x02:
        klen, index = decode_uvarint(buf, index)
        key_str_bytes = buf[index : index + klen]
        return key_str_bytes.decode("utf8"), index + klen
    if key_type_bits == 0x03:
        klen, index = decode_uvarint(buf, index)
        key_bytes = buf[index : index + klen]
        return key_bytes, index + klen
    raise TypeError("Invalid key type in control byte %02x" % key_type_bits)


# Policy: we ARE doing zero-value signalling.
# Policy: data types 15 and up are encoded as a seperate uvarint immediately following the control byte,
#         and the control byte's data type bits are set to all 1 (x0f) to signify this.
