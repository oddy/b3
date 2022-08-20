# Dynamic-recursive composite pack/unpack  (like json.dumps/loads)

from b3.datatypes import LIST, DICT, b3_type_name
from b3.guess_type import guess_type
from b3.item import encode_item, decode_header, decode_value

# See bottom of file for design policy notes.


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

    if isinstance(item, list):  # transform item to bytes, note recursive call
        item = b"".join([pack(item=i, rlimit=rlimit - 1) for i in item])
        data_type = LIST

    elif isinstance(item, dict):  # transform item to bytes, note recursive call
        item = b"".join([pack(item=v, key=k, rlimit=rlimit - 1) for k, v in item.items()])
        data_type = DICT

    else:
        data_type = guess_type(item)  # may blow up here encountering unknown types

    header_bytes, value_bytes = encode_item(key, data_type, item)

    if with_header:
        return b"".join([header_bytes, value_bytes])
    else:
        return value_bytes


def new_container(data_type):
    out = {LIST: list(), DICT: dict()}[data_type]
    return out


def unpack(buf, index=0):
    """Unpacks byte data to a new filled container object (list or dict).
    buf    - bytes data,
    index  - where to start in buf (defaults to 0)
    - as unpack expects a header which has container object type
      and data length, it doesn't need an end argument."""

    dkey, data_type, has_data, is_null, data_len, index = decode_header(buf, index)

    if data_type not in (DICT, LIST):
        emsg = "Expecting list or dict first, but got %s" % (b3_type_name(data_type))
        raise TypeError(emsg)

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
        key, data_type, has_data, is_null, data_len, index = decode_header(buf, index)

        if data_type in (LIST, DICT):
            value = new_container(data_type)
            unpack_into(value, buf, index, index + data_len)  # note recursive
        else:
            value = decode_value(data_type, has_data, is_null, data_len, buf, index)

        # --- Put data value into container ---
        if isinstance(out, list):
            out.append(value)
        elif isinstance(out, dict):
            out[key] = value
        else:
            raise TypeError("unpack_into only supports list or dict container objects")

        # --- Advance index ---
        index += data_len  # decode_header sets data_len=0 for us if is_null is on

    return out


# Policy: Unlike the schema encoder we DO recurse. We also treat the incoming message as authoritative and do less validation.

# --- Encoder/Pack policies ---
# policy: because there's no schema backing us, we dont know what incoming-to-pack missing data types SHOULD be!
# policy: Weird edge case: if the encoder gets a None, we consider that BYTES, because the header needs to encode *something* as the data type.
# policy: in practice None supercedes data-type checking here and in the schema packer, so this should be ok.

# --- Decoder/Unpack policies ---
# Policy: we're not hardwiring top-level it to a list like the old version did, so we HAVE to have a top-level header at the front anyway
#         the users just want list in list out, dict in dict out, etc.i
#         AND this actually makes the code a LOT simpler.
# Note:   The recursive unpack function takes a given container object (list, dict) as an argument, so if users already
#         have a container object of their own, they can call the recursive unpacker function directly.
