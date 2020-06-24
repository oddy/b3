
from b3.utils import SBytes
from b3.type_varint import *


# --- Varint API ---

def test_uvarint_enc():
    assert encode_uvarint(50)    == SBytes("32")
    assert encode_uvarint(500)   == SBytes("f4 03")
    assert encode_uvarint(50000) == SBytes("d0 86 03")
    assert encode_uvarint(0)     == SBytes("00")                    # note: NOT compact zero-value mode

def test_uvarint_dec():
    assert decode_uvarint(SBytes("32"), 0)       == (50, 1)
    assert decode_uvarint(SBytes("f4 03"), 0)    == (500, 2)
    assert decode_uvarint(SBytes("d0 86 03"), 0) == (50000, 3)

def test_svarint_enc():
    assert encode_svarint(50)   == SBytes("64")
    assert encode_svarint(-50)  == SBytes("63")
    assert encode_svarint(123456789)  == SBytes("aa b4 de 75")
    assert encode_svarint(-123456789) == SBytes("a9 b4 de 75")

def test_svarint_dec():
    assert decode_svarint(SBytes("64"), 0)       == (50, 1)
    assert decode_svarint(SBytes("63"), 0)       == (-50, 1)
    assert decode_svarint(SBytes("aa b4 de 75"), 0)  == (123456789, 4)
    assert decode_svarint(SBytes("a9 b4 de 75"), 0)  == (-123456789, 4)


# --- Codec varint API ---

def test_codec_uvarint_enc():
    assert codec_encode_uvarint(50000) == SBytes("d0 86 03")
    assert codec_encode_uvarint(0)     == SBytes("")            # Note: compact zero-value mode

def test_codec_svarint_enc():
    assert codec_encode_svarint(50000) == SBytes("a0 8d 06")
    assert codec_encode_svarint(0)     == SBytes("")            # Note: compact zero-value mode


def test_codec_uvarint_dec():                           # just making sure the index isnt returned
    assert codec_decode_uvarint(SBytes("d0 86 03"), 0, 4) == 50000
    assert codec_decode_uvarint(SBytes("00"),0,1) == 0
    assert codec_decode_uvarint(SBytes(""),0,0) == 0                      # note: compact zero-value mode

def test_codec_svarint_dec():
    assert codec_decode_svarint(SBytes("aa b4 de 75"), 0, 4)  == 123456789
    assert codec_decode_svarint(SBytes("a9 b4 de 75"), 0, 4)  == -123456789
    assert codec_decode_svarint(SBytes("00"),0,1) == 0
    assert codec_decode_svarint(SBytes(""),0,0) == 0                      # note: compact zero-value mode


# --- Notes for benchmarking ---
# https://pypi.org/project/pyinstrument/
# pip install pyinstrument
# pyinstrument benchmarks.py

# or..
# from pyinstrument import Profiler
# profiler = Profiler()
# profiler.start()
# profiler.stop()
# print(profiler.output_text(unicode=True, color=True))






