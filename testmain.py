
from   varint import encode_varint, decode_varint
from hexdump import hexdump                         # note this wraps stdout
from pprint import pprint

# * top level is ALWAYS a list.
# * We dont do the entire message's total length etc, that's up to the outer user.
#   - b/c it could be just a file in the case of C3
#   - and even with the streamy ones we might not be reading everything into memory all at once, so knowing the totlen there is less useful.
# * senders should pretty much always know how many items are gonna be in their top-level message anyway.

# * len-first means the underlying items have to be creatable and sizable FIRST. I am ok with that.
#   - the only 'streamy' build use case is prepending items to BMQ messages, which is on the item-level anyway.
#   - and we have the WIRE_SKIP hack to twiddle the top-level list len if we really need it.

# * Top level list-structure does NOT start with a type tag because we always know what type it is.

# Lets do a full in-memory parser/builder first, then break it down into different APIs

# --- Protobuf-compatible wiretypes ---
WIRE_VARINT  = 0            # a varint follows
# WIRE_64BIT   = 1            # little endian
WIRE_BYTES   = 2            # varint length then byte string
# WIRE_32BIT   = 5            # little endian

# I'm abusing the purity of wiretypes to e-z hack in lists and dicts.

# --- BagTag-specific wiretypes ---
WIRE_SKIP    = 7           # a varint follows & its the number of bytes to skip forward after it.
WIRE_LIST    = 3           # as BYTES but theres a list structure in there
WIRE_DICT    = 4           # as BYTES but theres a dict structure in there


def encode_tag(tag, wire_type):
    return (tag << 3) | wire_type

def decode_tag(tag_varint):
    tag,wire_type = tag_varint >> 3, tag_varint & 7
    return tag, wire_type

# Figure out what to do with various common types.
# BMQv3 just does "its bytes or let json deal with it" which was a good compromise at the time but we can do better.
# Note: figure out the list/buf dichotomy for building, as we go.

def BuildItem(tag_num, itm):
    out = []
    if isinstance(itm, list):
        out.append( encode_varint(encode_tag(tag_num, WIRE_LIST)) )
        l_buf = BuildListBuf(itm)                                       # note recursion
        out.append( encode_varint(len(l_buf)) )
        out.append(l_buf)

    elif isinstance(itm, dict):
        out.append( encode_varint(encode_tag(tag_num, WIRE_DICT)) )
        d_buf = BuildDictBuf(itm)                                       # note recursion
        out.append( encode_varint(len(d_buf)) )
        out.append(d_buf)

    elif isinstance(itm, int):
        out.append( encode_varint(encode_tag(tag_num, WIRE_VARINT)) )
        out.append( encode_varint(itm) )

    elif isinstance(itm, bytes):
        out.append( encode_varint(encode_tag(tag_num, WIRE_BYTES)) )
        out.append( encode_varint(len(itm)) )
        out.append(bytes(itm))

    else:
        raise NotImplementedError('Unknown item type %s'%itm.__class__)

    return ''.join(out)


def BuildListBuf(in_list):
    out = []
    out.append( encode_varint(len(in_list)) )
    for tagn, itm in enumerate(in_list):
        out.append( BuildItem(tagn, itm) )
    return ''.join(out)                             # note joiner MUST ALWAYS be '' otherwise extreme badness will happen


def BuildDictBuf(in_dict):
    out = []
    out.append( encode_varint(len(in_dict)) )
    keys = sorted(in_dict.keys())                   # todo: figure out what the other language's stance is on dictionary key order etc.
    for tagn,k in enumerate(keys):
        if not isinstance(k, basestring):   raise TypeError("Sorry, dict keys need to be strings")
        out.append( encode_varint(len(k)) )             # key name len
        out.append( k )                                 # key name
        out.append( BuildItem(tagn, in_dict[k]))        # value item
    return ''.join(out)

# a parser that cares about the tag numbers, and a parser that doesn't
# depending on if there's a tag dict (tag number, tag name) supplied.

def ParseItem(buf, index=0):
    # --- item tag ---
    tagv,index = decode_varint(buf, index)
    tag,wire   = decode_tag(tagv)
    print '-> item tag %d  wire %d' % (tag, wire)

    if wire == WIRE_VARINT:
        print '   decoding varint'
        val, index = decode_varint(buf, index)
        return index,val,tag

    elif wire == WIRE_LIST:
        print '   decoding list'
        l_buf_len,index = decode_varint(buf, index)
        l_buf = buf[index:index+l_buf_len]
        index += l_buf_len
        l_list = ParseListBuf(l_buf, 0)
        print '   done decoding list'
        return index,l_list,tag

    elif wire == WIRE_DICT:
        print '   decoding dict'
        d_buf_len,index = decode_varint(buf, index)
        d_buf = buf[index:index+d_buf_len]
        index += d_buf_len
        d_dict = ParseDictBuf(d_buf, 0)
        print '   done decoding dict'
        return index,d_dict,tag

    elif wire == WIRE_BYTES:
        print '   decoding bytes'
        data_len,index = decode_varint(buf, index)
        data = buf[index:index+data_len]
        index += data_len
        return index,data,tag

    else:
        raise NotImplementedError("Unknown wire type %d" % wire)


#  expects entire buf in one byte string
def ParseListBuf(buf, index=0):
    buf = bytes(buf)
    out = []
    nitems,index = decode_varint(buf, index)
    for n in range(nitems):
        index,itm,tagn = ParseItem(buf, index)
        out.append(itm)
    return out


def ParseDictBuf(buf, index=0):
    buf = bytes(buf)
    out = {}
    nitems,index = decode_varint(buf, index)
    for n in range(nitems):
        klen,index = decode_varint(buf, index)          # key string len
        k = buf[index:index+klen]                       # key string
        index += klen
        index,itm,tagn = ParseItem(buf, index)          # value item (tagn likely 0 or conflict, etc)
        out[k] = itm
    return out


def TestMain():
    print 'Building buf'
    list_1 = ["Hello", 123, "world","test1","test2"]
    list_2 = ["Hello", "world", "test1",123, "foooo", 456]
    list_3 = ["Hello", ["foo","bar"], "world"]
    list_4 = [69, ["level 2 #1", ["level 3 #1","level 3 #2"], "level 2 #2"], "level 1 #1"]
    list_5 = [69, {"key1":"value1", "key2":"value2", '2':3 }, {"a":{"b":999}}, 70]

    listx = list_5

    pprint(listx)
    buf = BuildListBuf(listx)
    print hexdump('buf1',buf)

    print
    print 'parsing buf'
    out = ParseListBuf(buf)
    pprint(out)





if __name__ == '__main__':
    TestMain()








