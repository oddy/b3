
# Locked-in policies:

# Item:
# [BYTE type]    [VARINT tag] <[VARINT namelen] [UTF8 name]>  [VARINT len] [BYTES data]
# ---type----    ------------------- key -------------------  ---------- value --------

# * Type high bit is 'key follows yes/no'
# * Tag 0 is 'name string follows'.

# Bag:
# [item][item][item][item-type END]
# * End of input also counts as END. (so we only need END for nested bags)

# * we will have a bit of a type zoo, but we currently have 128 possible type values so this is ok imo.
# * the type values are used for basic types (bytes, varint, false etc) and structure (bag, end-of-bag etc)

#  policies:

# Start the types at 1, and work up, in case we need to do another bit-eat for something.
# we might have e.g TYPE_LIST_BAG type, but just as a hint to the parser rather than any control over inner items.
# This means type varint doesnt need a length, and neither do any fixed number types.


END = '\x00'          # legit 'type' because no key, convention says no len or size either.
TYPE_END = 0          # - bag level type that says this bag is done. (only need it for nested bags) Note: now we have types without lengths.
TYPE_BAG = 1          # - upperlevel type that is a bag inside
TYPE_BYTES = 3
TYPE_VARINT = 4
TYPE_STRING = 5
TYPE_NONE = 6
TYPE_UTF8 = 7

TYPE_LIST_BAG = 8
TYPE_DICT_BAG = 9

# TYPE_TIME


# TYPE ZOO:
# float/double, various kinds of int,  bool?? enum?
# 'timestamp' 'duration'  'struct' 'FieldMask' (whatever the hell that is),  null, empty.
# bags have as_list and as_dict returners.

import struct, six
import codecs
from   pprint import pprint

from   varint import encode_varint, decode_varint, decode_varint0
from   hexdump import hexdump
from   six import PY2


# py2 atm
known_types = { int:TYPE_VARINT,  bytes:TYPE_BYTES, unicode:TYPE_STRING }
type_encode = { TYPE_VARINT:encode_varint,  TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.encode }
type_decode = { TYPE_VARINT:decode_varint0, TYPE_BYTES:lambda x:x, TYPE_STRING:codecs.decode }

if PY2:                                                             # "python 2 must be the special case"
    def EnsureUtf8(in_str):
        if isinstance(in_str, str):     return in_str                   # str & bytes are the same type.
        if isinstance(in_str, unicode): return in_str.encode('utf8')
        raise TypeError('Expected bytes, str or unicode type')
else:
    def EnsureUtf8(in_str):
        if isinstance(in_str, bytes):   return in_str
        if isinstance(in_str, str):     return in_str.encode('utf8')
        raise TypeError('Expected str or bytes type')



def BuildItem2(tag, item, typ=None):
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
    if typ == TYPE_END:     return index,typ,0,None

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
        if typ == TYPE_END:     break
        bag_out.append(data)                        # just the data atm, ignoring tags
        if index >= len(buf):       break
    return index, bag_out


# pytest -s -v -l ttlvx.py -k "build_item" && tree /F d:\tmp\testing\ffs


# Item:
# [BYTE type]    [VARINT tag] <[VARINT namelen] [UTF8 name]>  [VARINT len] [BYTES data]
# ---type----    ------------------- key -------------------  ---------- value --------

# using a varint item,
# test an item with no key
# test an item with a tag
# test an item with a name

# PackItem(tag, item_data, type=TYPE_BYTES)    # tag can be None


# WARNING: on python2, str becomes TYPE_BYTES. If you want TYPE_STRING either supply unicode input or supply TYPE_BYTES override.


# complex type packers



# bytes_override is only used if the detected type from PackBasic is TYPE_BYTES. It's for setting up tags etc.

def PackItem(item_data, tag=None, bytes_override=None):              # returns a packed ITEM

    # --- Convert item from Python type ---
    data_type, data_bytes = PackType(item_data)
    if bytes_override and data_type == TYPE_BYTES:
        data_type = bytes_override

    # --- Type byte ---
    out = [ struct.pack('B', data_type) ]
    if tag:     out[0] |= 0x80                      # set/clear tag-present bit
    else:       out[0] &= 0x7f

    # --- Tag (key) ---
    if isinstance(tag, int):                        # Normal
        out.append(encode_varint(tag))
    else:
        tag_b = EnsureUtf8(tag)
        out.append(encode_varint(len(tag_b)))
        out.append(tag_b)

    # --- Data (value) ---
    out.append(encode_varint(len(data_bytes)))
    if data_bytes:
        out.append(data_bytes)

    return ''.join(out)



# un-tagged complex type packers

def PackListNotags(in_list):                                            # returns a packed BAG of items (which you would pass to PackItem to turn into an item
    return ''.join([PackItem(i) for i in in_list]) + END                # returns BAG format

def PackDictNotags(in_dict):
    return ''.join([PackItem(v,k) for k,v in in_dict.items()]) + END    # return BAG format


# This returns a BT type number and a bytes buffer. Will access an override registry if we ever implement one.
def PackType(itm):
    if isinstance(itm, bytes):                  # pass through.
        return TYPE_BYTES, itm                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.

    if PY2 and isinstance(itm, unicode):
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, str):                    # Py3 unicode str only, py2 done by the bytes check above.
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, int):
        return TYPE_VARINT, encode_varint(itm)

    # ... Moar ...
    #if isinstance(itm, (list, dict)):   raise TypeError('PackBasicType does not accept composite types, use Pack instead')

    if isinstance(itm, list):
        return TYPE_LIST_BAG, PackListNotags(itm)

    if isinstance(itm, dict):
        return TYPE_DICT_BAG, PackDictNotags(itm)

    raise NotImplementedError('PackBasicType Unknown type %r' % type(itm))




# packtem is for base items. If you pass it a dict or list it barfs.
# - because passing dicts and lists is done as buffers, they have to be packed first.
# - because we need the size! packitem needs a size.



# Turn Base Item into Bytes
# Add some Bytes we already have as an overridden type (BAG vs BYTES)

# ---
# a good lens for this is the DateTime
# 1) Turn a DateTime into TYPE_EPOCH_NANOSEC
# 2) Turn the same DateTime into TYPE_EPOCH_SEC


















# Guess data type with override

# base types that need converting
# types that are BYTES with a type override (e.g. BAG)

# 'i want this number to be a fixed32'

# 1) bytes in, set type_override to this specifically.
# 2) not bytes in, convert it to bytes


# on python3, strings vs bytes are unambiguous

# on python2, unicode in = TYPE_STRING,  str in = TYPE_BYTES



def DataToBytes(data_type, data):           # return data_len (can be None), data_bytes (can be None)



    # Common case is bytes type data with a len
    data = bytes(data)
    return len(data), data



def test_build_item_varint_no_key():
    data = 'hello'
    buf = PackItem(None, data)
    assert buf[0] & 0x80 == 0



    assert False



# def TestMain():
#     sub_bag = PackItem(9,'-9-') + PackItem(8,'-8-') + chr(TYPE_BAG_END)
#     bagbuf1 = PackItem(33, 'hello') + PackItem(34, sub_bag, typ=TYPE_BAG) + PackItem(44, 'world') + PackItem(55, 'bar') + chr(TYPE_BAG_END)
#     bagbuf2 = PackItem(66, 6) + PackItem(77, 7) + PackItem(88, 8) + chr(TYPE_BAG_END)
#     mainbuf = PackItem(111, bagbuf1, typ=TYPE_BAG) + PackItem(222, bagbuf2, typ=TYPE_BAG) + PackItem(333, 333) + chr(TYPE_BAG_END)
#
#     print(hexdump('bagbuf1',bagbuf1))
#     print
#     print(ParseBag(mainbuf, 0))
#
#
#
# def TestMain1():
#     buf = PackItem(1, 77665427)
#     print(hexdump('buf1', buf))
#     g,idx = ParseItem(buf,0)
#     print(g.__class__)
#     print(repr(g))
#

# if __name__ == '__main__':
#     TestMain()









