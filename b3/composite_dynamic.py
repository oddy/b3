
# Dynamic-recursive composite pack/unpack  (like json.dumps/loads)

from b3.datatypes import B3_BYTES, B3_LIST, B3_DICT, b3_type_name
from b3.type_codecs import CODECS
from b3.guess_type import guess_type
from b3.item_header import encode_header, decode_header


def pack(item, key=None, with_header=True, rlimit=20):
    """Packs a list or dict to bytes.
       item        - the list or dict to pack
       with_header - returned bytes include a header. unpack() needs this on,
                     unpack_into() and embedding into schema fields needs it off.
       key         - key value for the top-level header (optional, typically not needed)
       rlimit      - recurse limit. Raises ValueError if limit exceeded.
       - see guess_type.py for the B3 types chosen, given certain Python types."""
    if rlimit < 1:
        raise ValueError("Recurse limit exceeded")
    data_type = B3_BYTES

    # --- Data ---
    if item is None:
        field_bytes = b""

    elif isinstance(item, bytes):
        field_bytes = item

    elif isinstance(item, list):
        field_bytes = b"".join([pack(item=i, rlimit=rlimit-1) for i in item])                     # Note: recursive call
        data_type   = B3_LIST

    elif isinstance(item, dict):
        field_bytes = b"".join([pack(item=v, key=k, rlimit=rlimit-1) for k, v in item.items()])   # Note: recursive call
        data_type   = B3_DICT

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
    out = {B3_LIST:list(), B3_DICT: dict()}[data_type]
    return out


def unpack(buf, index=0):
    """Unpacks byte data to a new filled container object (list or dict).
       buf    - bytes data,
       index  - where to start in buf (defaults to 0)
       - as unpack expects a header which has container object type
         and data length, it doesn't need an end argument. """

    data_type, key, is_null, data_len, index = decode_header(buf, index)

    if data_type not in (B3_DICT, B3_LIST):
        errmsg = "Expecting list or dict first in message, but got type %s" % (b3_type_name(data_type),)
        raise TypeError(errmsg)

    out = new_container(data_type)
    unpack_into(out, buf, index, index + data_len)
    return out


def unpack_into(out, buf, index, end):
    """Unpacks bytes data to a given container object.
       out   - container (list or dict) to fill with data,
       buf   - bytes data,
       index - where to start in buf,
       end   - where to stop in buf
       - use this function directly if you already have a container to put things into.
       - or if you want to specify start and end explicitly."""

    while index < end:
        # --- do header ---
        data_type, key, is_null, data_len, index = decode_header(buf, index)

        # --- get data value ---
        if is_null:
            value = None

        elif data_type == B3_BYTES:
            value = buf[index : index+data_len]

        elif data_type in (B3_LIST, B3_DICT):
            value = new_container(data_type)
            unpack_into(value, buf, index, index + data_len)       # note recursive

        else:
            _,DecoderFn = CODECS[data_type]
            value = DecoderFn(buf, index, index+data_len)

        # --- Put data value into container ---
        if isinstance(out, list):
            out.append(value)
        elif isinstance(out, dict):
            out[key] = value
        else:
            raise TypeError("unpack_into only supports list or dict container objects")

        # --- Advance index ---
        index += data_len       # decode_header sets data_len=0 for us if is_null is on

    return out



# Policy: Unlike the schema encoder we DO recurse. We also treat the incoming message as authoritative and do less validation.

# --- Encoder/Pack policies ---
# policy: because there's no schema backing us, we dont know what incoming-to-pack missing data types SHOULD be!
# policy: Weird edge case: if the encoder gets a None, we consider that B3_BYTES, because the header needs to encode *something* as the data type.
# policy: in practice None supercedes data-type checking here and in the schema packer, so this should be ok.

# --- Decoder/Unpack policies ---
# Policy: we're not hardwiring top-level it to a list like the old version did, so we HAVE to have a top-level header at the front anyway
#         the users just want list in list out, dict in dict out, etc.i
#         AND this actually makes the code a LOT simpler.
# Note:   The recursive unpack function takes a given container object (list, dict) as an argument, so if users already
#         have a container object of their own, they can call the recursive unpacker function directly.


