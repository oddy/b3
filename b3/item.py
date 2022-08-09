
from six import int2byte

from b3.utils import VALID_STR_TYPES, VALID_INT_TYPES, IntByteAt
from b3.type_varint import encode_uvarint, decode_uvarint
from b3.datatypes import B3_BOOL  # abstraction break: we are the bool 'codec' using the UF bit.
from b3.type_codecs import ENCODERS, ZERO_VALUE_TABLE

# Item:
# [header BYTE] [15+ type# UVARINT] [key (see below)] [data len UVARINT]  [ data BYTES ]
# ---------------------------- item_header -----------------------------  --- codecs ---

# --- header byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | has data   |null/zero/UF| key type   | key type   | data type  | data type  | data type  | data type  |
# +------------+------------+------------+------------+------------+------------+------------+------------+

# Note: UF = User Flag, can be used by codecs (e.g. bool) when has_data is True.

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

# -----------------------------------------------------------

# The 4 kinds of bool we can have:
# null bool                         NULL
# zero flagged bool                 FALSE
# has data bool with UF = False     FALSE
# has data bool with UF = True      TRUE

# -----------------------------------------------------------

# so bools can have has-data=True with data_len=0 which breaks our api

# the encode_header API is bad because
# we cant transmit the bool value into it.
# because is_null is for if something is null!  Not for transmitting the bool value.

# Which means we cant transmit it OUT of decode_header either because we lose null-vs-UF

# So we DO need to NZU-ize the header API after all.


# Think about special codecs that might want access to that bit.
# The most straightforward thing to do would be to make them both explicit.

# And the prod code actually calls the header apis only 3 times each
# so making it explicit would not be much more work.







# --- Key types ---
# +------------+------------+
# | key type   | key type   |
# +------------+------------+
#     0   0  (0)    no key
#     0   1  (4)    UVARINT
#     1   0  (8)    UTF8 bytes
#     1   1  (c)    raw bytess



def type_value_to_header_and_field_bytes(data_type, value):
    # in: type, value   out:  has_data, is_null, field_bytes

    # The 5 kinds of scenario, null, bool, zero, codec, bytes  (special codec)

    # defaults ('there is data')
    field_bytes = b""
    has_data = True
    is_null = False

    # Note that the order of these matters. Null supercedes zero, etc etc.

    if value is None:           # null value
        has_data = False
        is_null = True

    elif data_type == B3_BOOL:   # bool type
        is_null = value

    elif value == ZERO_VALUE_TABLE[data_type]:  # zero value
        has_data = False

    elif data_type in ENCODERS:       # codec-able value
        EncoderFn = ENCODERS[data_type]
        field_bytes = EncoderFn(value)
        # Note: we can: field_bytes, is_null = SpecialEncoderFn(value) in future if wanted.
    else:       # bytes value (bytes, dict, list, unknown data types)
        field_bytes = bytes(value)
        # Note: if the data type doesn't have a codec, it should be bytes-able.

    return has_data, is_null, field_bytes


# Note: we can: field_bytes, is_null = SpecialEncoderFn(value) in future if wanted.
# Policy: if the data type doesn't have a codec, it should be bytes-able.

def encode_item(key, data_type, value):
    value_bytes = b""
    has_data = True
    is_null = False

    # ======= Control flags and value bytes =======
    # Note that the order of these matters. Null supercedes zero, etc etc.
    if value is None:           # null value
        has_data = False
        is_null = True

    elif data_type == B3_BOOL:   # bool type
        is_null = value          # repurposes the null/zero flag to store its value

    elif value == ZERO_VALUE_TABLE[data_type]:  # zero value
        has_data = False

    elif data_type in ENCODERS:       # codec-able value
        EncoderFn = ENCODERS[data_type]
        value_bytes = EncoderFn(value)

    else:       # bytes value (bytes, dict, list, unknown data types)
        value_bytes = bytes(value)

    # ======= Header encoding =======
    ext_data_type_bytes = len_bytes = b""
    cbyte = 0x00

    # --- Null, data & data len ---
    if has_data:
        cbyte |= 0x80
    if is_null:
        cbyte |= 0x40
    if has_data and data_type is not B3_BOOL:  # has_data controls if there is a data length
        len_bytes = encode_uvarint(len(value_bytes))   # (except for BOOL where there is never a data length)

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
    header_bytes = b"".join([int2byte(cbyte), ext_data_type_bytes, key_bytes, len_bytes])
    return header_bytes, value_bytes







def encode_header(data_type, key=None, has_data=False, is_null=False, data_len=0):
    ext_data_type_bytes = len_bytes = b""
    cbyte = 0x00

    # --- Null, data & data len ---
    if has_data:
        cbyte |= 0x80
    if is_null:
        cbyte |= 0x40
    if has_data and data_type is not B3_BOOL:  # has_data controls if there is a data length
        len_bytes = encode_uvarint(data_len)   # (except for BOOL where there is never a data length)

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
    if has_data and data_type != B3_BOOL:
        data_len, index = decode_uvarint(buf, index)     # data len bytes
        is_null = False     # for API purposes, has_data forces is_null to false
        # we may extend this later to enable the is_null bit to be used as a user flag when has_data is true.
    else:
        is_null = bool(cbyte & 0x40)
        # Note: the B3_BOOL type uses is_null to report its actual value
        # Note: So it is the ONLY data type that doesn't have a length even with has_data on.

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


