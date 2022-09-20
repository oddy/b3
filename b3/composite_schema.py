# Schema-style composite encoder.

from b3.item import encode_item, decode_header, decode_value
from b3.utils import VALID_INT_TYPES
from b3.datatypes import b3_type_name, DICT, LIST

strict_mode = False
# strict pack: exception instead of ignore if input data has keys that are not in the schema.
# struct unpack: whether to insist the type be correct even if the value is null


def schema_lookup_key(schema, key):
    """return the schema entry given a key value. Try to match field names if non-number provided"""
    if isinstance(key, VALID_INT_TYPES):
        for field_def in schema:
            typ, name, n = field_def[:3]  # ignore additional schema fields
            if key == n:
                return typ, name, n
        return None, None, None
    else:
        for field_def in schema:     # ignore additional schema fields
            typ, name, n = field_def[:3]
            if key == name:
                return typ, name, n
        return None, None, None


def schema_pack(schema, data):
    """Packs a dict to bytes using a given schema.
    schema - list/tuple of (type, name, tag-number) values,
    data   - dict of data to pack
    - dict keys can match to schema using both string name or tag number.
    - nested fields with dicts or lists in them must be packed to bytes first.
    - schema fields that are missing from input data, are still packed but with value None.
    - packed data is always sorted by schema key number ascending"""
    if not isinstance(data, dict):
        raise TypeError("currently only dict input data supported by schema_pack")

    out = {}  # header and data items by schema_key_number

    for key, value in data.items():
        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)
        if schema_type is None:
            if strict_mode:
                raise KeyError("Supplied key %r is not in the schema" % (key,))
            else:
                continue

        if schema_type in (DICT, LIST) and not isinstance(value, bytes):
            emsg = "Please pack field #%r ('%s') to bytes first" % (
                schema_key_number,
                schema_key_name,
            )
            raise TypeError(emsg)

        out[schema_key_number] = encode_item(schema_key_number, schema_type, value)

    # Check schema fields that are missing from supplied data. Policy: Do it by NUMBER.
    for field_def in schema:
        mtyp, mname, mnum = field_def[:3]
        if mnum not in out:
            out[mnum] = encode_item(mnum, mtyp, None)
            # print("schema field %i missing from supplied, adding it with value None" % (mnum,))

    # Ensure outgoing message is sorted by key_number
    out_list = []
    for key_number in sorted(out.keys()):
        out_list.extend(out[key_number])
    return b"".join(out_list)


def schema_unpack(schema, buf, index=0, end=None):
    """Unpacks bytes to a dict using the given schema.
    schema - list/tuple of (type, name, tag-number) values,
    buf    - bytes data,
    index  - where to start in buf (if not given, defaults to 0),
    end    - where to stop in buf (if not given, defaults to len(buf),
    - if an incoming key is not found in the schema it is ignored.
    - if a schema key is not found in the incoming data it is added with value None.
    - if incoming data has no keys an error will occur (e.g. from pack()ing a list).
    - nested fields are returned as byte strings, will need unpacking too."""
    if end is None:
        end = len(buf)

    out = {}
    while index < end:
        key, data_type, has_data, is_null, data_len, index = decode_header(buf, index)
        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)

        if schema_type is None:  # key not found in schema, ignore and continue
            index += data_len  # skip over the unwanted data!
            continue

        # if not strict, only perform check if data is not null
        if (not (is_null and not has_data)) or strict_mode:
            if schema_type != data_type:
                emsg = "Field #%d ('%s') type mismatch - schema wants %s incoming has %s" % (
                    schema_key_number,
                    schema_key_name,
                    b3_type_name(schema_type),
                    b3_type_name(data_type),
                )
                raise TypeError(emsg)

        out[schema_key_name] = decode_value(data_type, has_data, is_null, data_len, buf, index)
        index += data_len

    # Check if any wanted fields are missing, add them with data=None
    # Policy: do this by whatever key type we are yielding (in this case, COMPUTED key name)
    for missing_key_name in set(i[1] for i in schema) - set(out.keys()):
        # print("key %r missing from incoming, adding it with value None" % (missing_key_name))
        out[missing_key_name] = None

    return out


# --- Outer design policies ---
# Policy: The null-flag (None in python) is a *seperate and distinct concept* from a type's zero-value
#         - It was decided to support null values because otherwise future uses would have to add explicit flag fields
#           for flagging the difference between a field being zero and a field being None.
#           Maybe protobuf people end up doing exactly that all the time, idk.
#           2022 they do its called "hazzers" and its terrible


# --- Design Policies ---
# policy: Function names - External API uses schema_pack (schema) and pack (dynamic), vs internal datatype stuff, which uses encode/decode.
# policy: we are currently mostly favouring correctness here because schema. Sometimes we favour simplicity or interop tho, as noted below.
# policy: string key search is case-insensitive for correctness and simplicity
# policy: we DONT accept fields with missing KEYS (e.g. created by dynrec-ing a List) - they will fail key-lookup.
#         The schema composite API is heavily dict-centric in python

# Policy: Members defined in the schema are ALWAYS present.
#         - they are also Null-Flagged going out by the encoder if they are missing from the OUTGOING data.
#         - They are set to None value by the decoder/unpacker/parser if they are missing from incoming data.
#         - with the null flag we still get full interop with the json/dyn-rec encoder.


# --- Encoder Policies ---
# policy: incoming fields that aren't found in the schema cause an error if strict is on. Good for dev, annoying for prod probably.
#         strict defaults to off currently.
# policy: favouring interop, schema fields that aren't found in the incoming dict are sent out with None values
#         So that the other end, if its a dynamic comp, still gets those keys present.
# Policy: outgoing messages ARE sorted by key_number - pretty sure C3 requires this!
# Policy: if there is no codec for the type, it's a yield-as-bytes-type.
# Policy: this API supports building bottom-up. Sub-fields have to be built first, then supplied to the outer schema pack call.
#         See the tests for how to do this.

# --- Decoder Policies ---
# Policy: missing values will be set to None.
# Policy: favouring correctness, incoming keys that aren't found in the schema are IGNORED.
# Policy: when 2+ fields come in that evaluate to the same computed key, we favour SIMPLICITY currently
#         - the last one in the message is yielded, because that requires no extra code to check and prioritise,
# todo:   we should maybe log that things are being ignored to help later users, but electing to Not Care for now.
# policy: we do NOT recurse like dynrec does, bytes-ey types are yielded as bytes. Up to the Caller to call us again with those bufs.
# Policy: favouring simplicity, this involves a buffer copy.
#         Yielding an index-pair would require the caller to understand that their dict data field was an index pair and not some bytes so we're not doing that for now.
# Policy: Matching incoming fields by key-number is standard operation, but we also allow for matching name by string (or bytes).
#         - incoming data with names was probably generated by a json-composite sender which is trying to be compatible.
#         - if two fields match to the same key, we favour simplicity and just yield the last one.


# Policy: schema type and message type are only checked for match if the value isn't None/NULL/Nil (None is its own type)
#         this is favouring interop over correctness.
