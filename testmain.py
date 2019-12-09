
from   varint import encode_varint, decode_varint
from hexdump import hexdump                         # note this wraps stdout

# * top level is ALWAYS a list.
# * We dont do the entire message's total length etc, that's up to the outer user.
#   - b/c it could be just a file in the case of C3
#   - and even with the streamy ones we might not be reading everything into memory all at once, so knowing the totlen there is less useful.
# * senders should pretty much always know how many items are gonna be in their top-level message anyway.




# Lets do a full in-memory parser/builder first, then break it down into different APIs

# --- Protobuf-compatible wiretypes ---
WIRE_VARINT  = 0            # a varint follows
WIRE_64BIT   = 1            # little endian
WIRE_BYTES   = 2            # varint length then byte string
WIRE_32BIT   = 5            # little endian

# I'm abusing the purity of wiretypes to e-z hack in lists and dicts.

# --- BagTag-specific wiretypes ---
WIRE_SKIP    = 15           # a varint follows & its the number of bytes to skip forward after it.
WIRE_LIST    = 14           # as BYTES but theres a list structure in there
WIRE_DICT    = 13           # as BYTES but theres a dict structure in there


def encode_tag(tag, wire_type):
    return (tag << 3) | wire_type

def decode_tag(tag_varint):
    tag,wire_type = tag_varint >> 3, tag_varint & 7
    return tag, wire_type


def MakeExampleBuf(in_list):
    out = []
    out.append( encode_varint(len(in_list)) )
    for tagn, itm in enumerate(in_list):
        if isinstance(itm, int):
            out.append( encode_varint(encode_tag(tagn, WIRE_VARINT)) )
        else:                                                               # for now assume everything else is bytes
            out.append( encode_varint(encode_tag(tagn, WIRE_BYTES)) )
            out.append( encode_varint(len(itm)) )
            out.append(bytes(itm))
    return ''.join(out)


# a parser that cares about the tag numbers, and a parser that doesn't
# depending on if there's a tag dict (tag number, tag name) supplied.

#  expects entire buf in one byte string
def ParseBuf(buf):
    buf = bytes(buf)
    index = 0
    out = []

    # Top level list-structure does NOT start with a type tag because we always know what type it is.
    # --- number of items ---

    nitems,index = decode_varint(buf, index)
    for n in nitems:

        # --- item tag ---
        tagv,index = decode_varint(buf, index)
        tag,wire   = decode_tag(tagv)

        if wire == WIRE_VARINT:
            val, index = decode_varint(buf, index)
            out.append(val)
        else:
            data_len,index = decode_varint(buf, index)
            data = buf[index:index+data_len]
            out.append(data)
            index += data_len

    return out
































def TestMain():
    list_1 = ["Hello", 123, "world"]
    buf = MakeExampleBuf(list_1)
    print hexdump('buf1',buf)




if __name__ == '__main__':
    TestMain()








