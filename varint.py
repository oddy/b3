


def encode_varint(num):
    _next = 1
    values = []
    while _next:
        _next = num >> 7
        shift = 128 if _next else 0
        part = (num & 127) | shift
        values.append(chr( part ))
        num = _next
    return ''.join(values)


def decode_varint(data, index):
    item = 128
    num = 0
    left = 0
    while item & 128:
        item = ord( data[index] )
        index += 1
        value = (item & 127) << left
        num += value
        left += 7
    return num, index
