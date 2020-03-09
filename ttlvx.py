
# Item:
# [BYTE type]    <[VARINT tag]>|<[VARINT namelen] [UTF8 name]>  [VARINT len] [BYTES data]
# ---type----    -------------------- key --------------------  ---------- value --------

# Bag:
# [item][item][item][END]
# * End of input also counts as END. (so we only need END for nested bags)

# * Type highest bit is 'key/tag follows yes/no'
# * Type 2nd-highest bit is 'key/tag is varint / utf8 string name'
# * we will have a bit of a type zoo, but we currently have 128 possible type values so this is ok imo.
# * the type values are used for basic types (bytes, varint, false etc) and structure (bag, end-of-bag etc)
# * TYPE_LIST_BAG types are just as a hint to the parser at that level, they dont control inner items.
# * !! ATM everything except the end-marker type has a value len, this may change. !!

# todo: fix the TYPE_END vs END thing.
# todo: figure out zero-copy unpacking. (passing indexes around vs copying sub-buffers)
# NOTE !!!!! b'' and u'' ALL CONSTANTS !!!!!!!!!
# NOTE byte buffer element access in py2 gives us small byte buffers (strs), in py3 gives us INTS.


END = b'\x00'          # The one 'type' that has no key and no value. Type 0 with the high bit set is illegal.
TYPE_END = 0          # - bag level type that says this bag is done. (only need it for nested bags) Note: now we have types without lengths.
TYPE_BAG = 1          # - upperlevel type that is a bag inside
TYPE_BYTES = 3
TYPE_VARINT = 4
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



# Note: basic type and item pack/unpack are the base building blocks.
# Note: composite type stuff is different for the different (json/protobuf/expect) use case systems.


# =====================================================================================================================
# = Base operations - Pack & Unpack
# =====================================================================================================================

# --- Pack ---

# In: a python object and an optional tag. Tag can be unicode string or integer.
# Out: the object converted to bytes and prepended with the necessary headers for its type and key info.

def Pack(item_data, tag=None, bytes_override=None):              # returns a packed ITEM
    # --- Convert item from Python type ---
    data_type, data_bytes = PackBasicType(item_data)
    if bytes_override and data_type == TYPE_BYTES:
        data_type = bytes_override

    # --- Type byte ---
    data_type &= 0x3f                                           # ensure data_type 0-63 / Clear top 2 bits for use by us
    if tag:                                 data_type |= 0x80           # set top bit if tag present
    if tag and not isinstance(tag, int):    data_type |= 0x40           # set 2-highest bit if tag is a string
    out = [ struct.pack('B', data_type) ]

    # --- Tag (key) ---
    if tag:
        if not isinstance(tag, int):                            # String tag
            tag_b = EnsureUtf8(tag)
            out.append(encode_varint(len(tag_b)))
            out.append(tag_b)
        else:                                                   # int tag
            out.append(encode_varint(tag))

    # --- Data (value) ---
    out.append(encode_varint(len(data_bytes)))
    if data_bytes:
        out.append(data_bytes)
    print("Pack out: %r" % out)
    return b''.join(out)


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
    if isinstance(itm, (list, dict)):   raise TypeError('Pack does not accept composite types, please use one of the composite APIs')
    raise NotImplementedError('PackBasicType Unknown type %r' % type(itm))



# --- Unpack ---

# In:  bytes buffer, index pointing to location in buffer
# Out: updated index, datatype, tag, converted data value

def Unpack(buf, index=0):
    if not isinstance(buf, bytes):      raise TypeError('Unpack takes only bytes buffers as input')
    print("\nunpack called with index=%r" % index)
    print(hexdump("unpack buf",buf))

    # --- Type byte ---
    type_b  = buf[index]                                    # str on py2, int on py3
    if PY2:   type_b = ord(type_b)                          # ord should be safe to use if we're ensured bytes coming in
    has_tag = bool(type_b & 0x80)
    tag_str = bool(type_b & 0x40)
    index += 1
    typ = type_b & 0x3f                                     # Actual data type number

    if typ == TYPE_END:                                          # we are at an TYPE_END marker, bail
        print("unpack we hit an end marker")
        return index,typ,0,None

    # --- Tag (key) ---
    tag = None                                              # no tag
    if has_tag:
        if tag_str:                                         # string tag
            print('got tag STRING tag')
            name_len,index = decode_varint(buf, index)
            name_b = buf[index : index+name_len]
            tag = name_b.decode('utf8')
            index += name_len
        else:                                               # int tag
            print('got tag INT tag')
            tag,index = decode_varint(buf, index)

    # --- Data (value) ---
    data_len,index = decode_varint(buf, index)
    print("unpack data_len %r" % data_len)
    val_buf = buf[index : index+data_len]
    print(hexdump("unpack val_buf",val_buf))
    if typ in [TYPE_BYTES, TYPE_BAG, TYPE_DICT_BAG, TYPE_LIST_BAG]:
        #value = (index,data_len)                           # zero-copy mode, caller has to copy buffer (if they want)
        value = val_buf                                     # not zero-copy mode.
    else:
        value = UnpackBasicType(val_buf, typ)
    index += data_len

    print("unpack returning index %r typ %r tag %r value %r" % (index,typ,tag,value))
    return index, typ, tag, value                           # the thin end of the unknowns-wedge


# In:  buffer, index, typecode
# Out: py-type value

def UnpackBasicType(val_buf, typ):            # not sure about the index juggling yet, lets see how we go. bytes types dont come through here.
    if typ == TYPE_UTF8:                                    # py2->unicode, py3->str
        return val_buf.decode('utf8')
    if typ == TYPE_VARINT:
        val,_ = decode_varint(val_buf, 0)                   # ???
        return val
    raise TypeError('Unknown type %d encountered' % typ)



# =====================================================================================================================
# = Composite recursive dict/list (json-style UX)
# =====================================================================================================================

# todo: recurse limits.
# todo: this allows int keys in dicts to become tag numbers. Do we want this?
# todo: - Possible security implications if mix-matched with schemaed messages that have number tags.

# return a list as bag data, not wrapped in a single item like PackRecursive does if you call IT with a list, and not with a end marker.
# this works because we always want top-level to be a list, not a dict.
# todo: cultural policy is currently to have top-level be a list always. Sub-levels can be dicts.

# --- Pack ---

def PackTopLevelList(itm_list):
    return b''.join([PackRecursive(i) for i in itm_list])

# Recursive function for packing dicts and lists (not using tag numbers, but does use tag names for the dicts)
def PackRecursive(itm, tag_name=None):
    if isinstance(itm, list):
        buf = b''.join([PackRecursive(i) for i in itm]) + END                # bag bytes...
        return Pack(buf, tag_name, bytes_override=TYPE_LIST_BAG)        # ...becomes item

    if isinstance(itm, dict):
        buf = b''.join([PackRecursive(v, k) for k, v in itm.items()]) + END  # bag bytes...
        return Pack(buf, tag_name, bytes_override=TYPE_DICT_BAG)        # ...becomes item

    out = Pack(itm, tag_name)
    print("PackRecursive out %r" % out)
    return out


# --- Unpack ---

def UnpackTopLevelList(buf, index=0):
    return UnpackRecursive(buf, index, container_type=TYPE_LIST_BAG)

def UnpackRecursive(buf, index, container_type):
    out = { TYPE_BAG: list(), TYPE_LIST_BAG : list(),  TYPE_DICT_BAG : dict() }[container_type]
    while True:
        index, typ, tag, val = Unpack(buf, index)
        if typ == TYPE_END:
            print("recur we hit an end marker")
            break

        if typ == TYPE_LIST_BAG or typ == TYPE_DICT_BAG:         # Note unpack gives us the bytes, we call ourselves to turn those bytes into a list/dict
            val = UnpackRecursive(val, 0, typ)                   # turn bytes into a dict or list for sub structures.
            # Note: we dont return or need a returned index in this case because val is a copied-buffer.
            # Note: if we move to zero-copy then we may have to pass indexes through. (but we also may not because of the
            # Note: higher-level bag having its own size at the higher level.)

        if container_type == TYPE_LIST_BAG:     out.append(val)
        if container_type == TYPE_BAG:          out.append(val)     # we're interpreting an un type-hinted bag as a list.
        if container_type == TYPE_DICT_BAG:     out[tag] = val

        if index >= len(buf):
            print("recur we hit end of input")
            break
    return out



# =====================================================================================================================
# = Composite manual (build/expect-style UX)
# =====================================================================================================================

# --- Unpack ---

def Expect(wanted_tags, buf, index=0):
    index, typ, tag, value = Unpack(buf, index)
    if tag not in wanted_tags:
        raise ValueError("Tag mismatch, expecting %r got %r" % (wanted_tags, tag))
    return index, tag, value


# For pack there are no additional helper functions, user just call Pack directly, like this:
    # sub_bag = Pack(9,'-9-') + Pack(8,'-8-') + END
    # bagbuf1 = Pack(33, 'hello') + Pack(34, sub_bag, bytes_override=TYPE_BAG) + Pack(44, 'world') + Pack(55, 'bar') + END
    # bagbuf2 = Pack(66, 6) + Pack(77, 7) + Pack(88, 8) + END
    # mainbuf = Pack(111, bagbuf1, bytes_override=TYPE_BAG) + Pack(222, bagbuf2, bytes_override=TYPE_BAG) + Pack(333, 333) + END

# --- Pack ---

def TestBuildExpectPack():
    buf = Pack(111, 1) + Pack('222', 2)
    index = 0
    index, tag, val = Expect([1,2,3], buf, index)
    print("1 Got tag %r val %r" % (tag,val))
    index, tag, val = Expect([3], buf, index)
    print("2 Got tag %r val %r" % (tag,val))
    # index, tag, val = Expect([1,2,3], buf, index)
    # print("3 Got tag %r val %r" % (tag,val))







# =====================================================================================================================
# = Tagged Schema-ed packing (protobuf-style UX)
# =====================================================================================================================

BASIC_TYPE_DEFAULTS = {             # like these are type defaults for AT THE USER LEVEL, so UTF8 becomes a u''. We can still use u'' in py3
    TYPE_BYTES      : b'',
    TYPE_UTF8       : u'',
    TYPE_VARINT     : 0,
}

# protobuf .proto files are 'optional' type name = tag_number;
# we can do type,name,number triples. And maybe [stretch goal] an sql-like CREATE TABLE-style syntax for expressing simple schemas.

schema1 = [(TYPE_VARINT, 'n1', 0), (TYPE_UTF8, 's1', 1), (TYPE_VARINT,'n2',3)]

# Schemas factory-make Messages.

# [parse] bytes -> [schema] -> message object  ->  as_dict, as_list, as_namedtuple, ['foo'], [3],  as_ordereddict
# [pack ] schema -> message object -> add field values -->  .pack()

# We're not inheriting we're composing.

class Schema(object):
    def __init__(s, type_name_numbers):
        s.triples = type_name_numbers
        s.by_num  = {i[2]:(i[0],i[1]) for i in s.triples}
        s.by_name = {i[1]:(i[0],i[2]) for i in s.triples}

    # --- Functions that create message objects ---

    def NewBlankMessage(s):
        msg = Message(s)            # note we supply ourselves to the message. Compose not inherit.
        return msg

    def MessageFromBytes(s, buf):
        msg = Message(s)

    # Takes bytes, makes a Message.

class Message(object):
    def __init__(s, schema_obj):
        s.schema = schema_obj
        s.items = {tag_num:BASIC_TYPE_DEFAULTS[typ] for typ,_,tag_num in s.schema.triples}
        s.named_items = {}          # directly-named items. overlay on top. numbered_items win if theres a same-name conflict.
        return

    # we're getting pretty speculative at this point. We just need to do enough here to make sure the binary format is OK.
    # aey attrdict styles.
    # getattr setattr
    # getitem setitem

    def __setitem__(s, key, value):
        if key in s.schema.by_name:
            tag = s.schema.by_name[key]
            s.items[tag] = value
        else:
            s.named_items[key] = value




# =====================================================================================================================
# = TESTING
# =====================================================================================================================



def TestListDict():
    x = [1,2,3,[4,5,6],[7,8,'9'],10,{11:{(99,88):13}},14]
    buf = PackTopLevelList(x)
    print(hexdump('listdict',buf))
    y = UnpackTopLevelList(buf,0)
    pprint(y)

def TestMain7():
    #fred = [1,2,3,[4,5],6,'7']
    fred = [{'a':'aa', 'b':'bb'}, 432]
    x = PackTopLevelList(fred)
    print(hexdump('x',x))
    print


# pytest -s -v -l ttlvx.py -k "build_item" && tree /F d:\tmp\testing\ffs

def test_build_item_varint_no_key():
    data = 'hello'
    buf = Pack(None, data)
    assert buf[0] & 0x80 == 0
    assert False


# def TestMain2():
#     sub_bag = Pack(9,'-9-') + Pack(8,'-8-') + chr(TYPE_BAG_END)
#     bagbuf1 = Pack(33, 'hello') + Pack(34, sub_bag, typ=TYPE_BAG) + Pack(44, 'world') + Pack(55, 'bar') + chr(TYPE_BAG_END)
#     bagbuf2 = Pack(66, 6) + Pack(77, 7) + Pack(88, 8) + chr(TYPE_BAG_END)
#     mainbuf = Pack(111, bagbuf1, typ=TYPE_BAG) + Pack(222, bagbuf2, typ=TYPE_BAG) + Pack(333, 333) + chr(TYPE_BAG_END)
#
#     print(hexdump('bagbuf1',bagbuf1))
#     print
#     print(ParseBag(mainbuf, 0))

#
# def TestMain1():
#     buf = Pack(1, 77665427)
#     print(hexdump('buf1', buf))
#     g,idx = ParseItem(buf,0)
#     print(g.__class__)
#     print(repr(g))
#

if __name__ == '__main__':
    #TestListDict()
    TestBuildExpectPack()










