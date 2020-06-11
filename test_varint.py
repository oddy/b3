
from utils import SBytes
from type_varint import *


# --- Varint API ---

def test_uvarint_enc():
    assert encode_uvarint(50)    == SBytes("32")
    assert encode_uvarint(500)   == SBytes("f4 03")         # note: skipping 5000, its still 2 bytes
    assert encode_uvarint(50000) == SBytes("d0 86 03")

def test_uvarint_dec():
    assert decode_uvarint(SBytes("32"), 0)       == (50, 1)
    assert decode_uvarint(SBytes("f4 03"), 0)    == (500, 2)
    assert decode_uvarint(SBytes("d0 86 03"), 0) == (50000, 3)

def test_svarint_enc():
    assert encode_svarint(50)   == SBytes("64")
    assert encode_svarint(-50)  == SBytes("63")
    assert encode_svarint(123456789)  == SBytes("aa b4 de 75")
    assert encode_svarint(-123456789) == SBytes("a9 b4 de 75")

def test_varint_codec_dec():                           # just making sure the index isnt returned
    assert codec_decode_svarint(SBytes("aa b4 de 75"), 0, 4)  == 123456789
    assert codec_decode_svarint(SBytes("a9 b4 de 75"), 0, 4)  == -123456789
    assert codec_decode_uvarint(SBytes("d0 86 03"), 0, 4) == 50000

def test_svarint_dec():
    assert decode_svarint(SBytes("64"), 0)       == (50, 1)
    assert decode_svarint(SBytes("63"), 0)       == (-50, 1)
    assert decode_svarint(SBytes("aa b4 de 75"), 0)  == (123456789, 4)
    assert decode_svarint(SBytes("a9 b4 de 75"), 0)  == (-123456789, 4)
