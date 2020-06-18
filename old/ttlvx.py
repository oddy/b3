
# Item:
# [BYTE type]    <[VARINT tag]>|<[VARINT namelen] [UTF8 name]>  [VARINT len] [BYTES data]
# ---type----    -------------------- key --------------------  ---------- value --------

# Bag:
# [item][item][item][END_BYTE]
# * End of input also counts as END_BYTE. (so we only need END_BYTE for nested bags)

# * Type highest bit is 'key/tag follows yes/no'
# * Type 2nd-highest bit is 'key/tag is varint / utf8 string name'
# * we will have a bit of a type zoo, but we currently have 128 possible type values so this is ok imo.
# * the type values are used for basic types (bytes, varint, false etc) and structure (bag, end-of-bag etc)
# * TYPE_LIST_BAG types are just as a hint to the parser at that level, they dont control inner items.
# * !! ATM everything except the end-marker type has a value len, this may change. !!

# todo: fix the TYPE_END vs END_BYTE thing.
# todo: want to give len-less types a go.
# todo: figure out zero-copy unpacking. (passing indexes around vs copying sub-buffers)
# todo: - zero copy should only be a thing for the json-UX i reckon, and happen only there.
# todo: - which means we'll break up pack/unpack into just header-processing

# todo: the types in the schema UX aren't being enforced/checked properly yet.
# todo: - they need to be checked on the way IN on the PYTHON SIDE
# todo: - consider an attrdict with type checker __setitem__ ?
# NOTE !!!!! b'' and u'' ALL CONSTANTS !!!!!!!!!
# NOTE byte buffer element access in py2 gives us small byte buffers (strs), in py3 gives us INTS.


END_BYTE= b'\x00'          # The one 'type' that has no key and no value. Type 0 with the high bit set is illegal.
# not to be confused with
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

from   type_varint import encode_varint, decode_varint
from   hexdump import hexdump
from   six import PY2

if PY2:                                                                 # "python 2 must be the special case"
    # note: actually we are being strict and barfing if the input ISNT a unicode string.
    # note: we DONT want the input to be bytes
    def EnsureUtf8(in_str):
        # if isinstance(in_str, str):     return in_str                   # NOTE: we're straight up disallowing this. str & bytes are the same type.
        if isinstance(in_str, unicode): return in_str.encode('utf8')
        raise TypeError('Expected unicode type only for tag names')
else:
    def EnsureUtf8(in_str):
        # if isinstance(in_str, bytes):   return in_str                   # NOTE: we're straight up disallowing byte tagnames
        if isinstance(in_str, str):     return in_str.encode('utf8')
        raise TypeError('Expected str type only for tag names')


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
    if tag is not None:
        data_type |= 0x80                                       # set top bit if tag present
        if not isinstance(tag, int):
            data_type |= 0x40                                   # set 2-highest bit if tag is a string [not an int]

    out = [ struct.pack('B', data_type) ]

    # --- Tag (key) ---
    if tag is not None:
        if not isinstance(tag, int):                            # String tag
            tag_b = EnsureUtf8(tag)                             # non-string tag inputs will barf here.
            out.append(encode_varint(len(tag_b)))
            out.append(tag_b)
        else:                                                   # int tag
            out.append(encode_varint(tag))

    # --- Data (value) ---
    out.append(encode_varint(len(data_bytes)))
    if data_bytes:
        out.append(data_bytes)
    # print("Pack out: %r" % out)
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
    # print("\nunpack called with index=%r" % index)
    # print(hexdump("unpack buf",buf))

    # --- Type byte ---
    type_b  = buf[index]                                    # str on py2, int on py3
    if PY2:   type_b = ord(type_b)                          # ord should be safe to use if we're ensured bytes coming in
    has_tag = bool(type_b & 0x80)
    tag_str = bool(type_b & 0x40)
    index += 1
    typ = type_b & 0x3f                                     # Actual data type number

    if typ == TYPE_END:                                          # we are at an TYPE_END marker, bail
        # print("unpack we hit an end marker")
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
    # print("unpack data_len %r" % data_len)
    val_buf = buf[index : index+data_len]
    # print(hexdump("unpack val_buf",val_buf))
    if typ in [TYPE_BYTES, TYPE_BAG, TYPE_DICT_BAG, TYPE_LIST_BAG]:
        #value = (index,data_len)                           # zero-copy mode, caller has to copy buffer (if they want)
        value = val_buf                                     # not zero-copy mode.
    else:
        value = UnpackBasicType(val_buf, typ)
    index += data_len

    # print("unpack returning index %r typ %r tag %r value %r" % (index,typ,tag,value))
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
        buf = b''.join([PackRecursive(i) for i in itm]) + END_BYTE                # bag bytes...
        return Pack(buf, tag_name, bytes_override=TYPE_LIST_BAG)        # ...becomes item

    if isinstance(itm, dict):
        buf = b''.join([PackRecursive(v, k) for k, v in itm.items()]) + END_BYTE  # bag bytes...
        return Pack(buf, tag_name, bytes_override=TYPE_DICT_BAG)        # ...becomes item

    out = Pack(itm, tag_name)
    # print("PackRecursive out %r" % out)
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
    # sub_bag = Pack(9,'-9-') + Pack(8,'-8-') + END_BYTE
    # bagbuf1 = Pack(33, 'hello') + Pack(34, sub_bag, bytes_override=TYPE_BAG) + Pack(44, 'world') + Pack(55, 'bar') + END_BYTE
    # bagbuf2 = Pack(66, 6) + Pack(77, 7) + Pack(88, 8) + END_BYTE
    # mainbuf = Pack(111, bagbuf1, bytes_override=TYPE_BAG) + Pack(222, bagbuf2, bytes_override=TYPE_BAG) + Pack(333, 333) + END_BYTE

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

schema1 = [(TYPE_VARINT, 'n1', 0), (TYPE_UTF8, 's1', 1), (TYPE_VARINT,'n2',3)]
# Fpr schemas: we can do type,name,number triples. And maybe [stretch goal] an sql-like CREATE TABLE-style syntax for expressing simple schemas.
# Schemas factory-make Messages.
# [parse] bytes -> schema.BytesToMessage -> AttrDict object
# [pack ] AttrDict message with defaulted fields -> add field values -> schema.MessageToBytes -> bytes
# We're not inheriting we're composing.


class Schema(object):
    def __init__(s, type_name_numbers, allow_custom_fields=False):
        s.triples = type_name_numbers
        allowed_name_type = unicode if PY2 else str
        for _,name,_ in s.triples:
            if not isinstance(name,allowed_name_type):
                raise TypeError('Schema error - only %s type field names are allowed' % allowed_name_type)
        s.allow_custom_fields = allow_custom_fields
        s.by_num  = {i[2]:(i[0],i[1]) for i in s.triples}
        s.by_name = {i[1]:(i[0],i[2]) for i in s.triples}

    def NewMessage(s):
        msg = Message()
        for typ, name, tag in s.triples:
            msg[name] = BASIC_TYPE_DEFAULTS[typ]    # Defaults
        return msg

    # this is almost completely buf-driven atm. Because we're starting with a defaulted message,
    # todo: we're not disallowing custom fields yet, or checking anything against the schema.
    def BytesToMessage(s, buf, index=0):
        msg = s.NewMessage()
        while True:
            index, typ, tag, val = Unpack(buf, index)
            if typ == TYPE_END:     break
            if isinstance(tag, int):    tag = s.by_num[tag][1]      # tag number to field name
            msg[tag] = val                                          # note we are not recursing here. Messages are assumed to be single-level atm.
            if index >= len(buf):   break
        return msg

    # schema-driven with custom fields appended if that is enabled.
    # todo: crack - Pack largely ignores the explicit type given in the schema in favour of doing it's guess-type-from-value thing.
    # todo:       - correct way to do this would be check the incoming value's type against the schema's type and barf if its wrong.
    # todo:       - this means splitting pack up further into deal-with-type and prepend-header just like we planned.
    # todo:  ****  so then deal-with-type is either GuessType for the json UX or CheckValueTypeVsSchemaType for us.  ***
    def MessageToBytes(s, msg):
        out = []
        for typ,name,tag in s.triples:      # todo: ensure that msg[name] is of type typ, perhaps by splitting Pack into GuessType and PrependHeader or similar.
            out.append( Pack(msg[name], tag, bytes_override=typ) )

        if s.allow_custom_fields:
            custom = set(msg.keys()) - set(s.by_name.keys())        # this means the custom fields cant override the schema fields by definition
            for k in sorted(list(custom)):
                out.append( Pack(msg[k], k) )

        out.append(END_BYTE)                # todo: the END_BYTE vs TYPE_END thing again
        return b''.join(out)


# schema1 = [(TYPE_VARINT, 'n1', 0), (TYPE_UTF8, 's1', 1), (TYPE_VARINT,'n2',3)]

def TestSchemaedMessage():
    #test_schema = [(TYPE_VARINT, 'n1', 5)]
    test_schema =  [(TYPE_VARINT, u'n1', 0), (TYPE_UTF8, u's1', 1), (TYPE_VARINT,u'n2',3)]

    sch = Schema(test_schema, allow_custom_fields=True)
    m = sch.NewMessage()
    m[u'n1'] = 3
    m[u's1'] = u'hello'
    m[u'n2'] = 2
    m[u'custom'] = u'world'
    buf = sch.MessageToBytes(m)
    print(hexdump('sch',buf))

    m2 = sch.BytesToMessage(buf)
    pprint(m2)

    print("m2.n1     : ",m2.n1)
    print("m2.s1     : ",m2.s1)
    print("m2.custom : ",m2.custom)

    # test setattr
    m2.custom = 'fred'
    print(m2.custom)



# --- Used by certs & headers ---
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        for k,v in self.items():
            if isinstance(v, dict):
                self[k] = AttrDict(v)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, key, value):
        print('setattr called key ',key,'   value  ',value)
        self[key] = value

class Message(AttrDict):    pass


# =====================================================================================================================
# = TESTING
# =====================================================================================================================


def TestListDict():
    # x = [1,2,3,[4,5,6],[7,8,'9'],10,{11:{"(99,88)":u'13'}},14]
    x = list(range(50))
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

def TestVarints():
    g = encode_varint(64)
    print(hexdump(g, prefix='varint +ve'))
    #print(hexdump(prefix='varint -ve', encode_varint(-44)))            # infnite loop! memory error!


if __name__ == '__main__':
    # TestListDict()
    # TestBuildExpectPack()
    # TestSchemaedMessage()

    TestVarints()










