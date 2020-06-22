
# Dynamic-recursive composite encoder  (like json)

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

from .datatypes import B3_BYTES, B3_COMPOSITE_LIST, B3_COMPOSITE_DICT, b3_type_name
from .codecs import CODECS, guess_type
from .item_header import encode_header, decode_header


# Policy: Unlike the schema encoder we DO recurse. We also treat the incoming message as authoritative and do less validation.

# --- Encoder/Pack policies ---
# policy: because there's no schema backing us, we dont know what incoming-to-encode missing data types SHOULD be!
# policy: Weird edge case: if the encoder gets a None, we consider that B3_BYTES, because the header needs to encode *something* as the data type.
# policy: in practice None supercedes data-type checking here and in the schema composite, so this should be ok.

# todo:   recurse limit after which we bail.

# --- Decoder/Unpack policies ---
# Policy: we're not hardwiring top-level it to a list like the old version did, so we HAVE to have the top-level header at the front anyway
#         the users just want list in list out, dict in dict out, etc.i
#         AND this actually makes the code a LOT simpler.
# Note:   The recursive unpack function takes a given container object (list, dict) as an argument, so if users already
#         have a container object of their own, they can call the recursive unpacker function directly.


def pack(item, key=None, with_header=True, rlimit=20):
    """takes a list or dict, returns header & data bytes"""
    if rlimit < 1:
        raise ValueError("Recurse limit exceeded")
    data_type = B3_BYTES

    # --- Data ---
    if item is None:
        field_bytes = b""

    elif isinstance(item, bytes):
        field_bytes = item

    elif isinstance(item, list):
        field_bytes = b"".join([pack(item=i, rlimit=rlimit-1) for i in item])                 # Note: recursive call
        data_type   = B3_COMPOSITE_LIST

    elif isinstance(item, dict):
        field_bytes = b"".join([pack(item=v, key=k, rlimit=rlimit-1) for k, v in item.items()])   # Note: recursive call
        data_type   = B3_COMPOSITE_DICT

    else:
        data_type   = guess_type(item)                    # may blow up here encountering unknown types
        EncoderFn,_ = CODECS[data_type]
        field_bytes = EncoderFn(item)

    # --- Header ---
    if with_header:
        header_bytes = encode_header(data_type=data_type, key=key, is_null=bool(item is None), data_len=len(field_bytes))
        return b"".join([header_bytes, field_bytes])
    else:
        return field_bytes



def new_container(data_type):
    out = { B3_COMPOSITE_LIST:list(), B3_COMPOSITE_DICT: dict() }[data_type]
    return out

# This one is the counterpart of pack with with_header=True (the default)
# Note: because unpack expects an header first up which has container object type and data len, it doesn't need an end argument.

def unpack(buf, index):
    """takes data buffer and start-index, returns a filled container object (list or dict).
    Requires buffer to have container-type header in it at the start.
    Use as counterpart to pack()"""

    data_type, key, is_null, data_len, index = decode_header(buf, index)

    if data_type not in (B3_COMPOSITE_DICT, B3_COMPOSITE_LIST):
        errmsg = "Expecting list or dict first in message, but got type %s" % (b3_type_name(data_type),)
        raise TypeError(errmsg)

    out = new_container(data_type)
    unpack_recurse(out, buf, index, index + data_len)
    return out

# users can call this one directly if they ** already have a container to put things into. **
# This one is the counterpart of pack with with_header=False (not the default)

# Note: recurse however DOES need, and use, an end argument.

def unpack_recurse(out, buf, index, end):
    """takes container object + data buffer & pointers, fills the container object & returns it."""
    while index < end:
        # --- do header ---
        data_type, key, is_null, data_len, index = decode_header(buf, index)

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


