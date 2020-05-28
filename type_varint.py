
import struct
import six
from   six import PY2, indexbytes, int2byte

# API level - unsigned (guard against negatives)
def encode_uvarint(num):
    if num < 0:     raise ValueError("encode_uvarint called with negative number")
    return encode_uvarint_actual(num)

# API level - signed (for negatives)
# ZigZag: bump it left one, and xor -1 with it IF its negative.
# lol if you dont xor it, uvarint does an infinite loop (because we're feeding uvarint a negative number)
# so the xor makes the number positive, i think
def encode_svarint(num):
    num = num << 1
    if num < 0:
        num = -1 ^ num
    return encode_uvarint_actual(num)

# API level - choose between signed and unsigned
def encode_varint(num):
    if num < 0:
        return encode_svarint(num)
    else:
        return encode_uvarint(num)

# Actual worker
def encode_uvarint_actual(num):                     # actual worker (also called by encode_svarint)
    _next = 1
    values = []
    while _next:
        _next = num >> 7
        shift = 128 if _next else 0
        part = (num & 127) | shift
        # values.append(struct.pack('B', part))     # 1.54 us  encoding value 50,000
        values.append(int2byte(part))               # 1.07 us  encoding value 50,000
        num = _next
    return b''.join(values)


# 3-byte input: py2 six 1.07us nosix 0.82us,  py3 six 1.14us nosix 1.1us

def decode_uvarint(data, index, end=None):
    item = 128
    num = 0
    left = 0
    while item & 128:
        item = indexbytes(data, index)      # TODO: benchmark  1.07us
        index += 1
        value = (item & 127) << left
        num += value
        left += 7
    return num, index


def decode_svarint(data, index, end=None):
    ux,index = decode_uvarint(data, index)
    x = ux >> 1
    if ux & 0x01 != 0:
        x = -1 ^ x
    return x,index





