
# Item:
# [BYTE type]    [VARINT tag] <[VARINT namelen] [UTF8 name]>  [VARINT len] [BYTES data]
# ---type----    ------------------- key -------------------  ---------- value --------

# Bag:
# [item][item][item][END]
# * End of input also counts as END. (so we only need END for nested bags)

# * Type high bit is 'key follows yes/no'
# * Tag 0 is 'name string follows'.
# * we will have a bit of a type zoo, but we currently have 128 possible type values so this is ok imo.
# * the type values are used for basic types (bytes, varint, false etc) and structure (bag, end-of-bag etc)
# * TYPE_LIST_BAG types are just as a hint to the parser at that level, they dont control inner items.
# * !! ATM everything except the end-marker type has a value len, this may change. !!

END = '\x00'          # The one 'type' that has no key and no value. Type 0 with the high bit set is illegal.
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

import struct
from   pprint import pprint

from   varint import encode_varint, decode_varint
from   hexdump import hexdump
from   six import PY2

if PY2:                                                                 # "python 2 must be the special case"
    def EnsureUtf8(in_str):
        if isinstance(in_str, str):     return in_str                   # str & bytes are the same type.
        if isinstance(in_str, unicode): return in_str.encode('utf8')
        raise TypeError('Expected bytes, str or unicode type')
else:
    def EnsureUtf8(in_str):
        if isinstance(in_str, bytes):   return in_str
        if isinstance(in_str, str):     return in_str.encode('utf8')
        raise TypeError('Expected str or bytes type')




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




# =====================================================================================================================
# = Packing base operations
# =====================================================================================================================


# In: a python object and an optional tag
# Out: the object converted to bytes and prepended with the necessary headers for its type and key info.

def PackItem(item_data, tag=None, bytes_override=None):              # returns a packed ITEM
    # --- Convert item from Python type ---
    data_type, data_bytes = PackBasicType(item_data)
    if bytes_override and data_type == TYPE_BYTES:
        data_type = bytes_override

    # --- Type byte ---
    if tag:     data_type |= 0x80                      # set/clear tag-present bit
    else:       data_type &= 0x7f
    out = [ struct.pack('B', data_type) ]

    # --- Tag (key) ---
    if tag:
        if isinstance(tag, int):                        # Normal
            if tag == 0:    raise ValueError('tag 0 is reserved for system use')
            out.append(encode_varint(tag))
        else:
            tag_b = EnsureUtf8(tag)
            out.append(encode_varint(0))                # tag number 0 means 'name follows'
            out.append(encode_varint(len(tag_b)))
            out.append(tag_b)

    # --- Data (value) ---
    out.append(encode_varint(len(data_bytes)))
    if data_bytes:
        out.append(data_bytes)

    return ''.join(out)


# In: a basic type item
# Out: the item's bagtag type number, and its representation as bytes.

def PackBasicType(itm):
    if isinstance(itm, bytes):                  # pass through.
        return TYPE_BYTES, itm                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.

    if PY2 and isinstance(itm, unicode):
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, str):                    # Py3 unicode str only, py2 done by the bytes check above.
        return TYPE_UTF8, itm.encode('utf8')

    if isinstance(itm, int):
        return TYPE_VARINT, encode_varint(itm)

    # ... Moar Types ...
    if isinstance(itm, (list, dict)):   raise TypeError('PackBasicType does not accept composite types, use Pack instead')
    raise NotImplementedError('PackBasicType Unknown type %r' % type(itm))




# =====================================================================================================================
# = Recursive no-tag packing
# =====================================================================================================================

# Intended for recursively packing dicts and lists of things, top down (?)
# return a list as bag data, not wrapped in a single item like PackRecursive does if you call IT with a list, and not with a end marker.
# this works because we always want top-level to be a list, not a dict.

def PackTopLevelList(itm_list):
    return ''.join([PackRecursive(i) for i in itm_list])

# Recursive function for packing dicts and lists (not using tag numbers, but does use tag names for the dicts)
def PackRecursive(itm, tag_name=None):
    if isinstance(itm, list):
        buf = ''.join([PackRecursive(i) for i in itm]) + END                # bag bytes...
        return PackItem(buf, tag_name, bytes_override=TYPE_LIST_BAG)        # ...becomes item

    if isinstance(itm, dict):
        buf = ''.join([PackRecursive(v, k) for k, v in itm.items()]) + END  # bag bytes...
        return PackItem(buf, tag_name, bytes_override=TYPE_DICT_BAG)        # ...becomes item

    return PackItem(itm, tag_name)





# =====================================================================================================================
# = TESTING
# =====================================================================================================================

def TestMain():
    #fred = [1,2,3,[4,5],6,'7']
    fred = [{'a':'aa', 'b':'bb'}, 432]
    x = PackTopLevelList(fred)
    print(hexdump('x',x))
    print


# pytest -s -v -l ttlvx.py -k "build_item" && tree /F d:\tmp\testing\ffs

def test_build_item_varint_no_key():
    data = 'hello'
    buf = PackItem(None, data)
    assert buf[0] & 0x80 == 0
    assert False


# def TestMain2():
#     sub_bag = PackItem(9,'-9-') + PackItem(8,'-8-') + chr(TYPE_BAG_END)
#     bagbuf1 = PackItem(33, 'hello') + PackItem(34, sub_bag, typ=TYPE_BAG) + PackItem(44, 'world') + PackItem(55, 'bar') + chr(TYPE_BAG_END)
#     bagbuf2 = PackItem(66, 6) + PackItem(77, 7) + PackItem(88, 8) + chr(TYPE_BAG_END)
#     mainbuf = PackItem(111, bagbuf1, typ=TYPE_BAG) + PackItem(222, bagbuf2, typ=TYPE_BAG) + PackItem(333, 333) + chr(TYPE_BAG_END)
#
#     print(hexdump('bagbuf1',bagbuf1))
#     print
#     print(ParseBag(mainbuf, 0))

#
# def TestMain1():
#     buf = PackItem(1, 77665427)
#     print(hexdump('buf1', buf))
#     g,idx = ParseItem(buf,0)
#     print(g.__class__)
#     print(repr(g))
#

if __name__ == '__main__':
    TestMain()









