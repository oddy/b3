
import struct

def encode_varint(num):
    _next = 1
    values = []
    while _next:
        _next = num >> 7
        shift = 128 if _next else 0
        part = (num & 127) | shift
        values.append(struct.pack('B', part))
        num = _next
    return b''.join(values)

def decode_varint0(data):
    index = 0
    item = 128
    num = 0
    left = 0
    while item & 128:
        item = struct.unpack('B', data[index])[0]
        #item = ord( data[index] )
        index += 1
        value = (item & 127) << left
        num += value
        left += 7
    return num


def decode_varint(data, index):
    item = 128
    num = 0
    left = 0
    while item & 128:
        item = struct.unpack('B', data[index])[0]
        #item = ord( data[index] )
        index += 1
        value = (item & 127) << left
        num += value
        left += 7
    return num, index
