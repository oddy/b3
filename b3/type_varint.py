# Codec for UVARINT SVARINT Signed and unsigned varint types

# Note: this module is used internally a lot and also supplies codecs.
# Note: the decoder function call API is different to the internal-use call API.
#       codec-use decode takes an end-index parameter, internal-use decode returns an updated index
# This is because varints are self-sizing, but the codecs always operate with known-size items because TLV.

# Note: This (followed by item_header) will be the first things to C-ify as they dominate the pyinstrument/cProfile results.

from six import indexbytes, int2byte

# --- Encoders ---

# API level - unsigned (guard against negatives)
def encode_uvarint(num):
    if num < 0:
        raise ValueError("encode_uvarint called with negative number")
    return encode_uvarint_actual(num)


# API level - signed (for negatives)
# ZigZag: bump it left one, and xor -1 with it IF its negative.
# lol if you dont xor it, uvarint encoder does an infinite loop (because we're feeding uvarint a negative number)
# so the xor makes the number positive, i think
def encode_svarint(num):
    num = num << 1
    if num < 0:
        num = -1 ^ num
    return encode_uvarint_actual(num)


# Actual worker
def encode_uvarint_actual(num):  # actual worker (also called by encode_svarint)
    _next = 1
    values = []
    while _next:
        _next = num >> 7
        shift = 128 if _next else 0
        part = (num & 127) | shift
        # values.append(struct.pack('B', part))     # 1.54 us  encoding value 50,000
        values.append(int2byte(part))  # 1.07 us  encoding value 50,000
        num = _next
    return b"".join(values)


# --- Internal-use Decoders ---
def decode_uvarint(data, index):
    item = 128
    num = 0
    left = 0
    while item & 128:
        item = indexbytes(data, index)
        index += 1
        value = (item & 127) << left
        num += value
        left += 7
    return num, index


def decode_svarint(data, index):
    ux, index = decode_uvarint(data, index)
    x = ux >> 1
    if ux & 0x01 != 0:
        x = -1 ^ x
    return x, index


# --- Codec-use Decoders ---
def codec_decode_uvarint(data, index, end):
    val, index2 = decode_uvarint(data, index)
    if index2 != end:
        raise ValueError("mismatch between tlv field size and uvarint data size")
    return val


def codec_decode_svarint(data, index, end):
    val, index2 = decode_svarint(data, index)
    if index2 != end:
        raise ValueError("mismatch between tlv field size and svarint data size")
    return val


# microbenchmark:
# 3-byte input: py2 six 1.07us nosix 0.82us,  py3 six 1.14us nosix 1.1us
