
from six import PY2
from hexdump import hexdump

from type_varint import encode_uvarint, decode_uvarint, encode_svarint, decode_svarint
from decimal import Decimal

from test_util import SBytes

from   collections import namedtuple

from type_sched import encode_sched_gen, encode_sched

# --- Basic types ---

# def test_pack_null():
#    assert PackNull(None)



def test_example():
    assert True


# def test_fail():
#     assert False




#
#
# def test_gen_tzname():
#
# def test_gen_xmas():
#     assert encode_sched_gen(-177794, is_days=True, subsec_exp=9, offset="-1045", tzname="Fred") == SBytes("f9 82 ed 0a ba 60 5e 1b 9a")






