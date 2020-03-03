
# Item:
# [BYTE type] [VARINT tag] <[VARINT namelen] [UTF8 name]> [VARINT len] [BYTES data]


# Bag:
# [item][item][item][item-of-type END_BAG]
# * And we only need BAG_END for nexted bags! End of input also counts as bag end.
# * end sentinel has totally won. End sentinel logic locked in.


# no-tag, tag-present, name-present

# problem with tag-0-requires-a-name is sometimes we dont want a tag OR a name. as in we're just doing lists.

# - Think we're gonna have to eat 2 bits in the type byte so each Item has switchable tag and name.
# - Because trying to control the format of Items from one layer up with a TYPE_DICT_BAG / TYPE_LIST_BAG
#   breaks the lovely simplicity we have just won ourselves, because you've got top-layer state reaching into all the lower level items.

# we could still have a TYPE_LIST_BAG type but it would be more of a hint than a full-control data structure.
# especially because the inner stuff either has already been seralized in a block that is e.g. signed, or
# has yet to be serialized and we'd have to pass a bunch of flags around.
# and thats just for building!

# we dont want tags to always be mandatory. Sometimes a list is just a list.
# This way we very simply get the best of ALL worlds.

# Decided thusly: 2 bits for tag on / name on.    # tag probably overrides name.


TYPE_0 = 0
TYPE_BAG = 255          # - upperlevel type that is a bag inside
TYPE_BAG_END = 254      # - bag level type that says this bag is done. (only need it for nested bags) Note: now we have types without lengths.
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


known_types = { int:TYPE_VARINT,  bytes:TYPE_BYTES, unicode:TYPE_STRING }
type_encode = { TYPE_VARINT:encode_varint,  TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.encode }
type_decode = { TYPE_VARINT:decode_varint0, TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.decode }




def BuildItem(tag, item, typ=None):
    out = []
    if not typ:
        cls = item.__class__
        typ = known_types[cls]
        fn = type_encode[typ]
        data = fn(item)
    else:                       # a typ is given instead of autodetected, assume bytes-style treatment.
        data = item
    datalen = len(data)
    out.append(chr(typ))                        # [BYTE type]
    out.append(encode_varint(tag))              # [VARINT tag]
    out.append(encode_varint(datalen))          # [VARINT len]
    out.append(data)                            # [BYTES data]
    return ''.join(out)


def ParseItem(buf, index=0):
    typ = ord(buf[index]) ; index += 1          # [BYTE type]
    if typ == TYPE_BAG_END:     return index,typ,0,None

    tag,index = decode_varint(buf, index)       # [VARINT tag]
    datalen,index = decode_varint(buf, index)   # [VARINT len]

    if typ == TYPE_BAG:
        index, sub_bag = ParseBag(buf, index)
        return index, typ, tag, sub_bag

    databuf = buf[index:index+datalen]          # [BYTES data]
    fn = type_decode[typ]
    data = fn(databuf)
    index += datalen
    return index, typ, tag, data


def ParseBag(buf, index=0):                                                     # yield an ordered-dict
    # keep parsing items until we hit TYPE_BAG_END or end of buf
    bag_out = []
    while True:
        index, typ, tag, data = ParseItem(buf, index)
        if typ == TYPE_BAG_END:     break
        bag_out.append(data)                        # just the data atm, ignoring tags
        if index >= len(buf):       break
    return index, bag_out




def TestMain():
    sub_bag = BuildItem(9,'-9-') + BuildItem(8,'-8-') + chr(TYPE_BAG_END)
    bagbuf1 = BuildItem(33, 'hello') + BuildItem(34, sub_bag, typ=TYPE_BAG) + BuildItem(44, 'world') + BuildItem(55, 'bar') + chr(TYPE_BAG_END)
    bagbuf2 = BuildItem(66, 6) + BuildItem(77, 7) + BuildItem(88, 8) + chr(TYPE_BAG_END)
    mainbuf = BuildItem(111, bagbuf1, typ=TYPE_BAG) + BuildItem(222, bagbuf2, typ=TYPE_BAG) + BuildItem(333, 333) + chr(TYPE_BAG_END)

    print hexdump('bagbuf1',bagbuf1)
    print
    print ParseBag(mainbuf, 0)



def TestMain1():
    buf = BuildItem(1, 77665427)
    print hexdump('buf1', buf)
    g,idx = ParseItem(buf,0)
    print g.__class__
    print repr(g)


if __name__ == '__main__':
    TestMain()









