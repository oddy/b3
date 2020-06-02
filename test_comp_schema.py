
from utils import SBytes
from datatypes import *
from composite_schema import *



TEST_SCHEMA_1 = (
    (B3_UVARINT, u"number1", 1),
    (B3_UTF8,    u"string1", 2),
    (B3_BOOL,    u"bool1",   3)
)

# Bag:
# [item][item][item][END_BYTE]
# * End of input also counts as END_BYTE. (so we only need END_BYTE for nested bags)
# * the control byte and/or header for the bag itself is 'outside', upstairs at upstairs-es level. We do not deal with it here.

# Item:
# [header BYTE] [key (see below)] [data len UVARINT]  [ data BYTES ]
# -------------- item_header -----------------------  --- codecs ---


# take the schema and a dict with the stuff in it. produce bytes.

def test_composite_schema_enc_dict():
    test1 = dict(number1=69, string1=u"foo", bool1=True)

    number1_data   = u"45"                   # encode_uvarint(69)
    number1_header = u"41 09 01"             # encode_header(B3_UVARINT, 1, 1)
    string1_data   = u"66 6f 6f"             # encode_utf8(u"foo")
    string1_header = u"43 07 02"             # encode_header(B3_UTF8, 3, 2)
    bool1_data     = u"01"                   # encode_bool(True)
    bool1_header   = u"41 05 03"             # encode_header(B3_BOOL, 1, 3)
    test1_hex = " ".join([number1_header, number1_data, string1_header, string1_data, bool1_header, bool1_data])
    test1_buf = SBytes(test1_hex)

    assert encode_schema_comp(TEST_SCHEMA_1, test1)  == test1_buf



# todo: we would never actually DECLARE a B3_NULL as part of a schema, that would be pointless.
# todo: But what do we do if one comes in as one of our named/numbered fields?
# We use the Go concept of a Zero Value as a guide.
