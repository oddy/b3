
from six import PY2
from hexdump import hexdump

from varint import encode_uvarint, decode_uvarint, encode_svarint, decode_svarint
from datatypes import *
from decimal import Decimal

# --- Bytes visualising helper ---

if PY2:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return ''.join([chr(int(i,16)) for i in hex_bytes_str.split()])
else:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return bytes([int(i,16) for i in hex_bytes_str.split()])

def test_sbytes():
    foo = "0a 0a 40 40 64 64"
    assert SBytes(foo) == b"\x0a\x0a\x40\x40\x64\x64"
    bar = """
    64 65 66 67 68 69 70
    71 72 73 74 75 76 77
    """
    assert SBytes(bar) == b"\x64\x65\x66\x67\x68\x69\x70\x71\x72\x73\x74\x75\x76\x77"

# --- Varint API itself ---

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

def test_svarint_dec():
    assert decode_svarint(SBytes("64"), 0)       == (50, 1)
    assert decode_svarint(SBytes("63"), 0)       == (-50, 1)
    assert decode_svarint(SBytes("aa b4 de 75"), 0)  == (123456789, 4)
    assert decode_svarint(SBytes("a9 b4 de 75"), 0)  == (-123456789, 4)

# --- Basic types ---

# def test_pack_null():
#    assert PackNull(None)


# --- Arb Prec Decimal ---
# the 'significand' is what fancy people call the coef - the number that isn't the exponent.

# negative positive infinity  (tests infinity AND significand sign bits)
# nan and snan
# negative positive zero (test the no significand at all code path)
# number 1      (exp 0)
# number 2.01   (exp -2)
# number .12345678901234567890  (exp -20)

# bit 4 (0x80) : 0=number, 1=special
# bit 3 (0x40) : 0=+ve number, 1=-ve number
# bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo   [special] 0=nan 1=infinity
# bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows  [special] 0=qnan 1=snan

def test_decimal_sign_inf():
    assert encode_decimal( Decimal('+inf') ) == SBytes("a0")        # 1010
    assert encode_decimal( Decimal('-inf') ) == SBytes("e0")        # 1110

    # assert decode_decimal( SBytes("a0") )    == Decimal('+inf')
    # assert decode_decimal( SBytes("e0") )    == Decimal('-inf')

def test_decimal_nans():
    assert encode_decimal( Decimal('nan')  ) == SBytes("80")        # 1000
    assert encode_decimal( Decimal('snan') ) == SBytes("90")        # 1001

    # assert decode_decimal( SBytes("80") )    == Decimal('nan')       # 1000
    # assert decode_decimal( SBytes("90") )    == Decimal('snan')       # 1001


def test_decimal_zeros():
    assert encode_decimal( Decimal('0')  )   == SBytes("00")        # 0000 0000  & no signif
    assert encode_decimal( Decimal('-0') )   == SBytes("40")        # 0100 0000  & no signif

def test_decimal_smallexp():
    assert encode_decimal( Decimal('1')  )   == SBytes("00 01")     # 0000 0000  & signif 01
    assert encode_decimal( Decimal('2.01') ) == SBytes("22 c9 01")  # 0010 0010  & signif c9 01

def test_decimal_largeexp():
    x = Decimal('.123456789012345')                                 # 0010 1111 & signif the rest
    assert encode_decimal( x )               == SBytes("2f f9 be b7 b0 88 89 1c")
    y = Decimal('.1234567890123456789')                             # 0011 0000 exp 13  & signif the rest
    assert encode_decimal( y )               == SBytes("30 13 95 82 a6 ef c7 9e 84 91 11")
    z = -y                                                          # 0111 0000 exp 13  & signif the rest
    assert encode_decimal( z )               == SBytes("70 13 95 82 a6 ef c7 9e 84 91 11")

def test_decimal_sci():                                             # 0001 0000 exp 45  & signif 31
    assert encode_decimal( Decimal('69e49')) == SBytes("10 31 45")


def test_example():
    assert True

# def test_fail():
#     assert False

