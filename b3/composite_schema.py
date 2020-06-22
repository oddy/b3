
# Schema-style composite encoder.

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-encoder| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

# Method: Encoders assemble lists of byte-buffers, then b"".join() them. We take advantage of this often for empty/nonexistant fields etc.
# Method: Decoders always take the whole buffer, and an index, and return an updated index.

from b3.type_codecs import CODECS
from b3.item_header import encode_header, decode_header
from b3.utils import VALID_INT_TYPES
from b3.datatypes import b3_type_name

# Nested composite item structure is
# [hdr|data][hdr|data][hdr|--------data--------[hdr|data][hdr|data] etc
#                          [hdr|data][hdr|data]

def schema_lookup_key(schema, key):
    """return the schema entry given a key value. Try to match field names if non-number provided"""
    if isinstance(key, VALID_INT_TYPES):
        for typ,name,n in schema:
            if key == n:
                return typ,name,n
        return None,None,None
    else:
        for typ,name,n in schema:
            if key == name:
                return typ,name,n
        return None,None,None


def schema_pack(schema, data, strict=False):
    """In: schema - list/tuple of (type, name, number) tuples,   data - dict of key_name or key_number : data_value"""
    if not isinstance(data, dict):
        raise TypeError("currently only dict input data supported by schema_pack")
    out = {}                            # header and data items by schema_key_number
    for key, value in data.items():

        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)
        # print("lookup key %r returns typ %r name %r number %r" % (key, schema_type, schema_key_name, schema_key_number))
        if schema_type is None:
            if strict:
                raise KeyError("Supplied key %r is not in the schema" % (key,))
            else:
                continue

        # Note: this handles correctly the zero-value case, codec returns b"", data_len is then zero, encode_header sets has-data flag.
        field_bytes = b""
        if value is not None:
            if schema_type in CODECS:
                EncoderFn,_ = CODECS[schema_type]
                field_bytes = EncoderFn(value)
            else:
                field_bytes = bytes(value)      # Note: if the data type doesn't have a codec, it should be bytes-able.

        header_bytes = encode_header(data_type=schema_type, key=schema_key_number, data_len=len(field_bytes), is_null=bool(value is None))
        out[schema_key_number] = (header_bytes, field_bytes)

    # Check schema fields that are missing from supplied data. Policy: Do it by NUMBER.
    for mtyp,mname,mnum in schema:
        if mnum not in out:
            out[mnum] = (encode_header(data_type=mtyp, key=mnum, is_null=True), b"")
            # print("schema field %i missing from supplied, adding it with value None" % (mnum,))

    # Ensure outgoing message is sorted by key_number
    out_list = []
    for key_number in sorted(out.keys()):
        out_list.extend(out[key_number])
    return b"".join(out_list)


def schema_unpack(schema, buf, index, end):
    """Parse through buf, create and return a dict"""
    out = {}

    while index < end:
        data_type, key, is_null, data_len, index = decode_header(buf, index)
        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)

        if schema_type is None:                 # key not found in schema, ignore and continue
            index += data_len                   # skip over the unwanted data!
            continue

        if is_null:                             # Policy: None supercedes data_len and data type when returning here in python.
            data = None
        else:
            if schema_type != data_type:        # ensure message type matches schema type
                type_error_msg = "Field #%d ('%s') type mismatch - schema wants %s incoming has %s" \
                                 % (schema_key_number, schema_key_name, b3_type_name(schema_type), b3_type_name(data_type))
                raise TypeError(type_error_msg)

            if schema_type in CODECS:
                _,DecoderFn = CODECS[schema_type]
                # print("key %s decoderfn %r" % (schema_key_name, DecoderFn))
                # Policy: codecs must handle data_len==0 case, and return a zero-value for their type.
                data = DecoderFn(buf, index, index + data_len)
            else:
                data = buf[index : index + data_len]                    # buffer copy for simplicity.

            index += data_len

        out[schema_key_name] = data

    # Check if any wanted fields are missing, add them with data=None
    # Policy: do this by whatever key type we are yielding (in this case, COMPUTED key name)  # todo: check this
    for missing_key_name in ( set(i[1] for i in schema) - set(out.keys()) ):
        # print("key %r missing from incoming, adding it with value None" % (missing_key_name))
        out[missing_key_name] = None

    return out

# --- Outer design policies ---
# Policy: The null-flag (None in python) is a *seperate and distinct concept* from a type's zero-value
#         - It was decided to support null values because otherwise future uses would have to add explicit flag fields
#           for flagging the difference between a field being zero and a field being None.
#           Maybe golang people end up doing exactly that all the time, idk.

# Policy: Zero-values are supported with a Codec: return-no-bytes (=data_len 0) -> Header: data_lem 0 = !has_data flag

# --- Design Policies ---
# policy: Function names - External API uses schema_pack (schema) and pack (dynamic), vs internal datatype stuff, which uses encode/decode.
# policy: we are currently mostly favouring correctness here because schema. Sometimes we favour simplicity or interop tho, as noted below.
# todo: schema caching for fast lookup. and/or a slightly smart schema object.
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
# Policy: schema type and message type are only checked for match if the value isn't None/NULL/Nil (None is its own type)
#         this is favouring interop over correctness.
# Policy: when 2+ fields come in that evaluate to the same computed key, we favour SIMPLICITY currently
#         - the last one in the message is yielded, because that requires no extra code to check and prioritise,
# todo:   we should maybe log that things are being ignored to help later users, but electing to Not Care for now.
# policy: we do NOT recurse like dynrec does, bytes-ey types are yielded as bytes. Up to the Caller to call us again with those bufs.
# Policy: favouring simplicity, this involves a buffer copy.
#         Yielding an index-pair would require the caller to understand that their dict data field was an index pair and not some bytes so we're not doing that for now.
# Policy: Matching incoming fields by key-number is standard operation, but we also allow for matching name by string (or bytes).
#         - incoming data with names was probably generated by a json-composite sender which is trying to be compatible.
#         - if two fields match to the same key, we favour simplicity and just yield the last one.

