
import struct
import six
from   six import PY2, indexbytes, int2byte

def encode_uvarint(num):
    # todo: add a check for negative numbers here. Currently it infinite-loops.
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

# ZigZag: bump it left one, and xor -1 with it IF its negative.
# lol if you dont xor it, uvarint does an infinite loop (because we're feeding uvarint a negative number)
# so the xor makes the number positive
def encode_svarint(num):
    num = num << 1
    if num < 0:
        num = -1 ^ num
    return encode_uvarint(num)



















# def decode_uvarint(data, index):
#     item = 128
#     num = 0
#     left = 0
#     while item & 128:
#         item = data[index]
#         if PY2: item = ord(item)
#         index += 1
#         value = (item & 127) << left
#         num += value
#         left += 7
#     return num, index

# 3-byte input: py2 six 1.07us nosix 0.82us,  py3 six 1.14us nosix 1.1us

def decode_uvarint(data, index):
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






#
# # from protobuf
#
#   def DecodeVarint(buffer, pos):
#     result = 0
#     shift = 0
#     while 1:
#       b = six.indexbytes(buffer, pos)
#       result |= ((b & 0x7f) << shift)
#       pos += 1
#       if not (b & 0x80):
#         result &= mask
#         result = result_type(result)
#         return (result, pos)
#       shift += 7
#       if shift >= 64:
#         raise _DecodeError('Too many bytes when decoding varint.')
#   return DecodeVarint
#
#
# def _SignedVarintDecoder(bits, result_type):
#   """Like _VarintDecoder() but decodes signed values."""
#
#   signbit = 1 << (bits - 1)
#   mask = (1 << bits) - 1
#
#   def DecodeVarint(buffer, pos):
#     result = 0
#     shift = 0
#     while 1:
#       b = six.indexbytes(buffer, pos)
#       result |= ((b & 0x7f) << shift)
#       pos += 1
#       if not (b & 0x80):
#         result &= mask
#         result = (result ^ signbit) - signbit
#         result = result_type(result)
#         return (result, pos)
#       shift += 7
#       if shift >= 64:
#         raise _DecodeError('Too many bytes when decoding varint.')
#   return DecodeVarint
#
#
# def encode_varint(num):
#
#
#
#
#
# def decode_varint(data, index):
#
#
