
from decimal import Decimal

from test_util import SBytes
from datatypes import *
from varint import *


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

def test_sign_inf():
    assert encode_decimal( Decimal('+inf') ) == SBytes("a0")        # 1010
    assert encode_decimal( Decimal('-inf') ) == SBytes("e0")        # 1110

    # assert decode_decimal( SBytes("a0") )    == Decimal('+inf')
    # assert decode_decimal( SBytes("e0") )    == Decimal('-inf')

def test_nans():
    assert encode_decimal( Decimal('nan')  ) == SBytes("80")        # 1000
    assert encode_decimal( Decimal('snan') ) == SBytes("90")        # 1001

    # assert decode_decimal( SBytes("80") )    == Decimal('nan')       # 1000
    # assert decode_decimal( SBytes("90") )    == Decimal('snan')       # 1001


def test_zeros():
    assert encode_decimal( Decimal('0')  )   == SBytes("00")        # 0000 0000  & no signif
    assert encode_decimal( Decimal('-0') )   == SBytes("40")        # 0100 0000  & no signif

def test_smallexp():
    assert encode_decimal( Decimal('1')  )   == SBytes("00 01")     # 0000 0000  & signif 01
    assert encode_decimal( Decimal('2.01') ) == SBytes("22 c9 01")  # 0010 0010  & signif c9 01

def test_largeexp():
    x = Decimal('.123456789012345')                                 # 0010 1111 & signif the rest
    assert encode_decimal( x )               == SBytes("2f f9 be b7 b0 88 89 1c")
    y = Decimal('.1234567890123456789')                             # 0011 0000 exp 13  & signif the rest
    assert encode_decimal( y )               == SBytes("30 13 95 82 a6 ef c7 9e 84 91 11")
    z = -y                                                          # 0111 0000 exp 13  & signif the rest
    assert encode_decimal( z )               == SBytes("70 13 95 82 a6 ef c7 9e 84 91 11")

def test_sci():                                             # 0001 0000 exp 45  & signif 31
    assert encode_decimal( Decimal('69e49')) == SBytes("10 31 45")

