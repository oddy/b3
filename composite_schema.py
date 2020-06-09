
# Schema-style composite encoder.

# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

from datatypes import CODECS
from item_header import encode_header, decode_header
from utils import VALID_INT_TYPES


# --- item structure ---
# [header BYTE] [key (see below)] [data len UVARINT] [data BYTES]
# \------------------------------------------------/                            = handled here

# policy: we are currently mostly favouring correctness because schema. Sometimes we favour simplicity or interop tho, as noted below.
# todo: if there was a switch for "favour correctness vs favour interop" it would
# todo: control whether missing/incorrect fields blow up or get skipped.  skip_invalid=False = blow up, otherwise continue.
#       we may be able to get away with just having that as a flag param to the functions.
# policy: we DONT accept fields with missing keys (e.g. created by dynrec-ing a List) - they will fail key-lookup.

# policy: we do NOT recurse like dynrec does, bytes-ey types are yielded as bytes. Up to the Caller to call us again with those bufs.
# Policy: favouring simplicity, this involves a buffer copy.
#         Yielding an index-pair would require the caller to understand that their dict data field was an index pair and not some bytes so we're not doing that for now.


# todo: schema caching for fast lookup. and/or a slightly smart schema object.
# policy: string key search is case-insensitive for simplicity
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

# Policy: outgoing messages ARE sorted by key_number
#         pretty sure C3 requires this!
# Policy: if there is no codec for the type, it's a yield-as-bytes-type.

# Policy: No need to support B3_END - everything is sized.
# if they want to encapsulate, the size is known. They build the sub-object to bytes, then add that item to their
# dict, then encode that. The sizes are always known because we're building bottom-up.

def encode_schema_comp(schema, data):
    """In: schema - list/tuple of (type, name, number) tuples,   data - dict of key_name or key_number : data_value"""
    if not isinstance(data, dict):
        raise TypeError("currently only dict input data supported by encode_schema_comp")
    out = {}                            # header and data items schema_key_number
    for key, value in data.items():
        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)
        if schema_type is None:
            # policy: favouring correctness, incoming keys that aren't found in the schema cause an error
            raise KeyError("Supplied key %r is not in the schema" % (key,))

        if value is None:
            header_bytes = encode_header(data_type=schema_type, key=schema_key_number, is_null=True)
            out[schema_key_number] = (header_bytes, b"")
        else:
            if schema_type in CODECS:
                EncoderFn,_ = CODECS[schema_type]
                field_bytes = EncoderFn(value)
            else:
                field_bytes = bytes(value)              # Note: value should be bytes already anyway at this point.
            header_bytes = encode_header(data_type=schema_type, key=schema_key_number, data_len=len(field_bytes))
            out[schema_key_number] = (header_bytes, field_bytes)

    # Check for schema fields that are missing from supplied data. Policy: Do it by NUMBER.
    for mtyp,mname,mnum in schema:
        if mnum not in out:
            print("schema field %i missing from supplied, adding it with value None" % (mnum,))
            out[mnum] = (encode_header(data_type=mtyp, key=mnum, is_null=True), b"")

    # Ensure outgoing message is sorted by key_number
    out_list = []
    for key_number in sorted(out.keys()):
        out_list.extend(out[key_number])
    return b"".join(out_list)


# Policy: missing values will be set to None.
# Policy: favouring correctness, incoming keys that aren't found in the schema are IGNORED.
# Policy: favouring interop OVER correctness, None values are allowed through even if the schema type and message type DONT match!
#         because in python the None type is it's own type
# Policy: when 2+ fields come in that evaluate to the same computed key, we favour SIMPLICITY currently
#         - the last one in the message is yielded, because that requires no extra code to check and prioritise,
# todo:   we should maybe log that things are being ignored to help later users, but electing to Not Care for now.
# todo: if data_len == 0  have the codec return its zero-value. The codecs do this by checking index and end tho so we dont need special handling for it here

def decode_schema_comp(schema, buf, index, end):
    """Parse through buf, create and return a dict"""
    out = {}
    while index < end:
        key, data_type, data_len, is_null, index = decode_header(buf, index)
        schema_type, schema_key_name, schema_key_number = schema_lookup_key(schema, key)

        if schema_type is None:
            print("Note: ignoring incoming key %r because its not in the schema" % (key,))
            continue

        if is_null:             # note we let None through even if the types mismatch.
            data = None
        else:
            if schema_type != data_type:        # ensure message type matches schema type
                type_error_msg = "Type mismatch for field %s (%d) - schema %d incoming %d" % (schema_key_name, schema_key_number, schema_type, data_type)
                raise TypeError(type_error_msg)

            if schema_type in CODECS:
                _,DecoderFn = CODECS[schema_type]
                data,_ = DecoderFn(buf, index, index + data_len)            # note: we are ignoring the decoderFn's returned index in favour of using data_len from the header
            else:
                data = buf[index : index + data_len]                      # Favoring simplicity, this is a buffer copy instead of some kind of zero-copy "inflict an index pair on the caller" thing.

            index += data_len                          # todo: this is a bit messy and we will fix it after making the dyn-rec encoders

        out[schema_key_name] = data

    # Check if any wanted fields are missing, add them with data=None
    # Policy: do this by whatever key type we are yielding (in this case, COMPUTED key name)
    for missing_key_name in ( set(i[1] for i in schema) - set(out.keys()) ):
        print("key %r missing from incoming, adding it with value None" % (missing_key_name))
        out[missing_key_name] = None

    return out  # ,end

# todo: return end?


# * Single level only, nonbasic types get surfaced as bytes. Caller must then call one of our APIs to unpack them in turn.
#   - yes this involves a buffer copy.

# * Members defined in the schema are ALWAYS present.
#   - They are set to None value by the parser if they are missing from incoming data.
#   - they are also Null-Flagged going out by the encoder if they are missing from the OUTGOING data.
#   - with the null flag we still get full interop with the json/dyn-rec encoder.

# * The null-flag (None in python) is a *seperate and distinct concept* from a type's zero-value
#   - It was decided to support null values because otherwise future uses would have to add explicit flag fields for flagging the
#     difference between a field being zero and a field being None.

# * [FUTURE] Zero-values should be encoded as a present header data len of 0. It will be the codecs' responsibility to handle that.

# * for additional, non-schemaed fields the schema-comp policy is they should NOT be packed.
#   - Currently we actuall blow up if non-schema fields are found. todo: consider skipping instead

# * for the parser, matching incoming data by number is standard operation, but we also allow for matching by string (or bytes).
#   - incoming data with names was probably generated by a json-composite sender which is trying to be compatible.
#   - if two fields match to the same key, we favour simplicity and just yield the last one.
#   - but this is really a Shouldnt Happen and You Have An Error In Your Code / Messages, Caller

