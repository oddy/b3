from   varint import encode_varint, decode_varint

END = '\x00'          # The one 'type' that has no key and no value. Type 0 with the high bit set is illegal.
TYPE_END = 0          # - bag level type that says this bag is done. (only need it for nested bags) Note: now we have types without lengths.
TYPE_BAG = 1          # - upperlevel type that is a bag inside
TYPE_BYTES = 3
TYPE_VARINT = 4
TYPE_STRING = 5
TYPE_NONE = 6
TYPE_UTF8 = 7
# TYPE_STRING vs TYPE_UTF8 - whatever is most obvious for the user (probably TYPE_STRING?)
TYPE_LIST_BAG = 8
TYPE_DICT_BAG = 9

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
        if index >= len(buf):   break
    return index, bag_out
