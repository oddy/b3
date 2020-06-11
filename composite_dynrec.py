
# Dynamic-recursive composite encoder  (like json)

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

from datatypes import CODECS, B3_BYTES, B3_BAG_LIST, B3_BAG_DICT, B3_BAG
from item_header import encode_header, decode_header
from dynrec_guesstype import guess_type


# Unlike the schema encoder we DO recurse. We also treat the incoming message as authoritative and do less validation.

# todo: recurse limit after which we bail.
# policy: because there's no schema backing us, we dont know what incoming-to-encode missing data types SHOULD be!
# policy: if we get a None, we consider that B3_BYTES, rather than having a NULL data type just for this one case.
# todo:   test & check the is_null logic supercedes correctly for this.

# At the top level we often just want the [item][item][item] bytes out, without a header-for-that tacked on the front.
# But recursive operation always needs the header on the front, ("this item that is a dict and its bytes are following")
# Users can totally call recurse directly and supply a key if they want.


# You know maybe we DO want the header surfaced, because then we can have list or dict top-level items...
# There's no way for it to know what the top-level item actuall is otherwise!
# Policy: we're not hardwiring it to a list like the old code did, so we HAVE to have the top-level header at the front anyway?
# Policy: the users just want to throw a dict in, get a dict out, etc.
# Note: its up to them to indicate that they DONT want a header on the very top then, if they already know "its always a dict" or whatever
#       - this is how i WAS thinking about it back then.
#       - thats also completely wrong in terms of actual usability, sigh.


def encode_dynrec_comp(item, key=None, with_header=True):
    """takes a datastructure (list or dict), returns bytes"""
    # while its possible to use this to convert a single type/value, its assumed that we never do that.

    is_null = False
    data_type = B3_BYTES         # policy: if we get a None, we consider that B3_BYTES, rather than having a NULL data type just for this one case.

    # --- Data ---
    if item is None:
        is_null = True
        field_bytes = b""

    elif isinstance(item, bytes):
        field_bytes = item

    elif isinstance(item, list):
        field_bytes = b"".join( [ encode_dynrec_comp(i) for i in item ] )               # Note: recursive call
        data_type = B3_BAG_LIST

    elif isinstance(item, dict):
        field_bytes = b"".join( [ encode_dynrec_comp(v, k) for k, v in item.items()])   # Note: recursive call
        data_type = B3_BAG_DICT

    else:
        data_type = guess_type(item)            # may blow up encountering unknown type
        EncoderFn,_ = CODECS[data_type]
        field_bytes = EncoderFn(item)

    # --- Header ---
    if with_header:
        header_bytes = encode_header(data_type=data_type, key=key, is_null=is_null, data_len=len(field_bytes))
        return b"".join([header_bytes, field_bytes])
    else:
        return field_bytes



# Policy: we turn untyped BAG into a list, currently.
def new_container(data_type):
    out = { B3_BAG: list(), B3_BAG_LIST : list(),  B3_BAG_DICT : dict() }[data_type]
    return out

# This one is the counterpart of encode_dynrec_comp with with_header=True (the default)

def decode_dynrec_comp(buf, index, end):
    """takes buffer and pointers, returns a container object (list or dict)"""
    if index >= end:    raise ValueError("index >= end")
    key, data_type, data_len, is_null, index = decode_header(buf, index)        # get the special top level header, to find out if we need to make a list or a dict.
    out = new_container(data_type)
    decode_dynrec_comp_recurse(out, buf, index, index+data_len)
    return out

# users can call this one directly if they already have a container to put things into.
# This one is the counterpart of encode_dynrec_comp with with_header=False (not the default)

def decode_dynrec_comp_recurse(out, buf, index, end):
    """takes container, buffer, pointers, and adds items to the container."""
    while index < end:
        # --- do header ---
        key, data_type, data_len, is_null, index = decode_header(buf, index)

        # --- get data value ---
        if is_null:
            value = None

        elif data_type == B3_BYTES:
            value = buf[index : index+data_len]

        elif data_type in (B3_BAG_LIST, B3_BAG, B3_BAG_DICT):
            value = new_container(data_type)
            decode_dynrec_comp_recurse(value, buf, index, index+data_len)       # note recursive

        else:
            _,DecoderFn = CODECS[data_type]
            value,_ = DecoderFn(buf, index, index+data_len)            # note: we are ignoring the decoderFn's returned index in favour of using data_len from the header

        # --- Put data value into container ---
        if isinstance(out, list):
            out.append(value)
        elif isinstance(out, dict):
            out[key] = value

        # --- Advance index ---
        if not is_null:
            index += data_len

    return


