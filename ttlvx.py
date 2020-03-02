
# Item:
# [BYTE type] [VARINT tag] <[VARINT namelen] [UTF8 name]> [VARINT len] [BYTES data]

# Bag:
# [VARINT nitems] [ITEM item1] [ITEM item2] etc

TYPE_0 = 0
TYPE_BAG = 1   #     - bytes that is a bag inside
TYPE_BYTES = 2
TYPE_VARINT = 3
TYPE_STRING = 4

# TYPE_TIME
# TYPE_STRING

# float/double, various kinds of int,  bool?? enum?
# 'timestamp' 'duration'  'struct' 'FieldMask' (whatever the hell that is),  null, empty.
# bags have as_list and as_dict returners.

# json has: number, string, list, dict, bool,

import codecs
from   pprint import pprint

from   varint import encode_varint, decode_varint, decode_varint0
from   hexdump import hexdump


# Still using the build list collapse model and the ,index model to begin with.

known_types = {int:TYPE_VARINT,  bytes:TYPE_BYTES, unicode:TYPE_STRING }
type_encode = {TYPE_VARINT:encode_varint,  TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.encode}
type_decode = {TYPE_VARINT:decode_varint0, TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.decode}

def BuildItem(tag, item):
    out = []
    cls = item.__class__
    typ = known_types[cls]

    fn = type_encode[typ]
    data = fn(item)
    datalen = len(data)

    out.append(chr(typ))                        # [BYTE type]
    out.append(encode_varint(tag))              # [VARINT tag]
    out.append(encode_varint(datalen))          # [VARINT len]
    out.append(data)                            # [BYTES data]
    return ''.join(out)


def ParseItem(buf, index=0):
    typ = ord(buf[index]) ; index += 1          # [BYTE type]
    fn = type_decode[typ]
    tag,index = decode_varint(buf, index)       # [VARINT tag]
    datalen,index = decode_varint(buf, index)   # [VARINT len]
    databuf = buf[index:index+datalen]          # [BYTES data]
    data = fn(databuf)
    index += datalen
    return data, index


def TestMain():
    buf = BuildItem(1, 77665427)
    print hexdump('buf1', buf)
    print
    g,idx = ParseItem(buf,0)
    print g.__class__
    print g

    return


if __name__ == '__main__':
    TestMain()









