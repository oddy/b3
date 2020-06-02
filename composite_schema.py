
# Packer Architecture:
# |Json UX/Composite Packer| ->(dict keynames)-> |Header-izer| <-(bytes)<- |Single-item ToBytes packer| <- |Datatype Packers|
# |Pbuf UX/Composite Packer| ->(tag numbers)  -^

from datatypes import CODECS
from item_header import encode_header, decode_header

# Schema-style composite types. (as opposed to json-style composite types)


# In: schema - tuple of (type, name, number) tuples,   data - dict

def encode_schema_comp(schema, data):
    if not isinstance(data, dict):
        raise TypeError("currently only dict input data supported by encode_schema_comp")

    out = []

    # todo: we are assuming schema is sorted by field_number
    for data_type, field_name, field_number in schema:
        field_data = data[field_name]
        EncoderFn,_ = CODECS[data_type]
        field_bytes = EncoderFn(field_data)
        header_bytes = encode_header(data_type=data_type, data_len=len(field_bytes), key=field_number)
        out.append(header_bytes)
        out.append(field_bytes)

    return b"".join(out)






# * Single level only, nonbasic types get surfaced as bytes. Caller must then call one of our APIs to unpack them in turn.
#   - yes this involves a buffer copy.

# * Members defined in the schema are ALWAYS present. They are zero-valued by the parser if they are missing from incoming data.
#   - they are also zero-valued going OUT by the PACKER if they are missing from the OUTGOING data.
#   - how appropriate this is, is really down to interactions between the schema composite and the json composite.
#   - over in the json-composite it would totally be beneficial to have keyed items existing but zero-flagged, as thats the only
#     way for the json-composite to know that those members should exist.
#   - so the whole "go zero value" ethos will lead us to seamless interop between schema-composite and json-composite which is REALLY NICE
#     people can upgrade from json-hackery to schema-ed goodness seamlessly without breaking anything.

# * zero values should not require any data transmission apart from the item header. (no data len if there is no data)
# * this may remove/obsolete the need for an actual NULL type, we will see.

# * for additional, non-schemaed fields the schema-comp policy is they should NOT be packed.

# - for the parser, matching incoming data by number is standard operation.
# - incoming data with names was probably generated by a json-composite sender which is trying to be compatible.
#   so IF we allow them (not-strict option) numbers should take precedence for security, maybe generate a warning somehow if there's a collision.
# - so really there should be one or the other, and possibly allowing named and byte-ed fields may even be a "strict" option.

#   but this is really a Shouldnt Happen and You Have An Error In Your Code, Caller



