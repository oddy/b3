
# Dynamic-recursive composite encoder  (like json)

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

from .datatypes import B3_BYTES, B3_COMPOSITE_LIST, B3_COMPOSITE_DICT
from .codecs import CODECS, guess_type
from .item_header import encode_header, decode_header


# Policy: Unlike the schema encoder we DO recurse. We also treat the incoming message as authoritative and do less validation.

# --- Encoder/Pack policies ---
# policy: because there's no schema backing us, we dont know what incoming-to-encode missing data types SHOULD be!
# policy: Weird edge case: if we get a None, we consider that B3_BYTES, because the header needs to encode *something* as the data type.
# policy: in practice None supercedes data-type checking here and in the schema composite, so this should be ok.
# todo:   test & check the is_null logic supercedes correctly for this.
# todo:   recurse limit after which we bail.

# Policy: we're not hardwiring top-level it to a list like the old version did, so we HAVE to have the top-level header at the front anyway
#         the users just want list in list out, dict in dict out, etc.
#         AND this makes the code a LOT simpler.
# Note:   its up to the users to indicate that they DONT want a header on the very top then, if they already know "its always a dict" or whatever


# Policy: small-scale bottom-up-assembly data items.
# bottom-up-assmbly means the size-in-bytes of everything is always known.
# Counter-Rationale: the only use cases blair and i could think of for unknown-size items are:
# 1) Huge datastructures (e.g. qsa tables) which will have their own sizing,
# 2) e.g. tcp comms big-long-streaming which should always be chunked anyway!


def pack(item, key=None, with_header=True):
    """takes a list or dict, returns header & data bytes"""
    is_null = False
    data_type = B3_BYTES

    # --- Data ---
    if item is None:
        is_null     = True
        field_bytes = b""

    elif isinstance(item, bytes):
        field_bytes = item

    elif isinstance(item, list):
        field_bytes = b"".join([pack(i) for i in item])                 # Note: recursive call
        data_type   = B3_COMPOSITE_LIST

    elif isinstance(item, dict):
        field_bytes = b"".join([pack(v, k) for k, v in item.items()])   # Note: recursive call
        data_type   = B3_COMPOSITE_DICT

    else:
        data_type   = guess_type(item)                    # may blow up here encountering unknown types
        EncoderFn,_ = CODECS[data_type]
        field_bytes = EncoderFn(item)

    # --- Header ---
    if with_header:
        header_bytes = encode_header(data_type=data_type, key=key, is_null=is_null, data_len=len(field_bytes))
        return b"".join([header_bytes, field_bytes])
    else:
        return field_bytes



def new_container(data_type):
    out = { B3_COMPOSITE_LIST:list(), B3_COMPOSITE_DICT: dict() }[data_type]
    return out

# This one is the counterpart of pack with with_header=True (the default)
def unpack(buf, index, end):
    """takes data buffer and pointers, returns a filled container object (list or dict).
    Requires buffer to have container-type header in it at the start.
    Use as counterpart to pack()"""
    if index >= end:
        raise ValueError("index >= end")

    key, data_type, is_null, data_len, index = decode_header(buf, index)

    if data_type not in (B3_COMPOSITE_DICT, B3_COMPOSITE_LIST):
        raise TypeError("Expecting list or dict container type first in message, but got %i" % (data_type,))

    out = new_container(data_type)
    unpack_recurse(out, buf, index, index + data_len)
    return out
    # todo: handling index==end ? return b"" ?


# users can call this one directly if they ** already have a container to put things into. **
# This one is the counterpart of pack with with_header=False (not the default)

def unpack_recurse(out, buf, index, end):
    """takes container object + data buffer & pointers, fills the container object & returns it."""
    while index < end:
        # --- do header ---
        key, data_type, is_null, data_len, index = decode_header(buf, index)

        # --- get data value ---
        if is_null:
            value = None

        elif data_type == B3_BYTES:
            value = buf[index : index+data_len]

        elif data_type in (B3_COMPOSITE_LIST, B3_COMPOSITE_DICT):
            value = new_container(data_type)
            unpack_recurse(value, buf, index, index + data_len)       # note recursive

        else:
            _,DecoderFn = CODECS[data_type]
            value = DecoderFn(buf, index, index+data_len)

        # --- Put data value into container ---
        if isinstance(out, list):
            out.append(value)
        elif isinstance(out, dict):
            out[key] = value
        else:
            raise TypeError("unpack_recurse only supports list or dict container objects")

        # --- Advance index ---
        index += data_len       # decode_header sets data_len=0 for us if is_null is on

    return


