
from decimal import Decimal

from test_util import SBytes
from hexdump import hexdump
from type_decimal import encode_decimal, decode_decimal

# --- Arb Prec Decimal ---
# the 'significand' is what fancy people call the coef - the number that isn't the exponent.

# negative positive infinity  (tests infinity AND significand sign bits)
# nan and snan
# negative positive zero (test the no significand at all code path)
# number 1      (exp 0)
# number 2.01   (exp -2)                   (internal exp)
# number .12345678901234567890  (exp -20)  (external exp)

# +------------+------------+------------+------------+------------+------------+------------+------------+
# | 0:Number   | Sign       | Expo Sign  | Ext exp(1) | exponent   | exponent   | exponent   | exponent   |
# | 1:Special  | Sign       | Nan/Inf(2) | q/s nan(3) | unused     | unused     | unused     | unused     |
# +------------+------------+------------+------------+------------+------------+------------+------------+
# (1) 0 = exponent in bottom 4 bits, 1 = exponent varint follows
# (2) 0 = NaN, 1 = Infinity
# (3) 0 = 'Quiet' NaN, 1 = 'Signalling' NaN

# --- Encode ---

def test_enc_decni_nans():
    assert encode_decimal( Decimal('nan')  ) == SBytes("80")        # 1000
    assert encode_decimal( Decimal('snan') ) == SBytes("90")        # 1001
    assert encode_decimal( Decimal('-nan') ) == SBytes("c0")        # 1100
    assert encode_decimal( Decimal('-snan')) == SBytes("d0")        # 1101

def test_enc_deci_sign_inf():
    assert encode_decimal( Decimal('+inf') ) == SBytes("a0")        # 1010
    assert encode_decimal( Decimal('-inf') ) == SBytes("e0")        # 1110


def test_enc_deci_zeros():
    assert encode_decimal( Decimal('0')  )   == SBytes("00")        # 0000 0000  & no signif
    assert encode_decimal( Decimal('-0') )   == SBytes("40")        # 0100 0000  & no signif

def test_enc_deci_smallexp():
    assert encode_decimal( Decimal('1')  )   == SBytes("00 01")     # 0000 0000  & signif 01
    assert encode_decimal( Decimal('2.01') ) == SBytes("22 c9 01")  # 0010 0010  & signif c9 01

def test_enc_deci_largeexp():
    x = Decimal('.123456789012345')                                 # 0010 1111 & signif the rest
    assert encode_decimal( x )               == SBytes("2f f9 be b7 b0 88 89 1c")
    y = Decimal('.1234567890123456789')                             # 0011 0000 exp 13  & signif the rest
    assert encode_decimal( y )               == SBytes("30 13 95 82 a6 ef c7 9e 84 91 11")
    z = -y                                                          # 0111 0000 exp 13  & signif the rest
    assert encode_decimal( z )               == SBytes("70 13 95 82 a6 ef c7 9e 84 91 11")

def test_enc_deci_sci():                                             # 0001 0000 exp 45  & signif 31
    assert encode_decimal( Decimal('69e49')) == SBytes("10 31 45")


# --- Decode ---

def test_dec_deci_nans():
    # assert decode_decimal( SBytes("80"), 0 )    == Decimal('nan')     # can't do because NaN == NaN is FALSE
    # assert decode_decimal( SBytes("90"), 0 )    == Decimal('snan')    # can't do because sNans raise exceptions
    assert str(decode_decimal(SBytes("80"),0,1)) == 'NaN'
    assert str(decode_decimal(SBytes("90"),0,1)) == 'sNaN'
    assert str(decode_decimal(SBytes("c0"),0,1)) == '-NaN'
    assert str(decode_decimal(SBytes("d0"),0,1)) == '-sNaN'

def test_dec_deci_sign_inf():
    assert decode_decimal( SBytes("a0"),0,1 )    == Decimal('+inf')
    assert decode_decimal( SBytes("e0"),0,1 )    == Decimal('-inf')


def test_dec_deci_zeros_withvalue():
    assert decode_decimal(SBytes("00 00"),0,2)  == Decimal('0')
    assert decode_decimal(SBytes("40 00"),0,2)  == Decimal('-0')

def test_dec_deci_zeros_novalue():
    assert decode_decimal(SBytes("00"),0,1)     == Decimal('0')
    assert decode_decimal(SBytes("40"),0,1)     == Decimal('-0')

def test_dec_deci_smallexp():
    assert decode_decimal(SBytes("00 01"),0,2)      == Decimal('1')
    assert decode_decimal(SBytes("22 c9 01"),0,3)   == Decimal('2.01')

def test_dec_deci_largeexp():
    buf = SBytes("2f f9 be b7 b0 88 89 1c")
    assert decode_decimal(buf,0,len(buf))     == Decimal('.123456789012345')
    buf = SBytes("30 13 95 82 a6 ef c7 9e 84 91 11")
    assert decode_decimal(buf,0,len(buf))     == Decimal('.1234567890123456789')
    buf = SBytes("70 13 95 82 a6 ef c7 9e 84 91 11")
    assert decode_decimal(buf,0,len(buf))     == Decimal('-.1234567890123456789')


def test_dec_deci_sci():
    assert decode_decimal(SBytes("10 31 45"),0,3)  == Decimal('69e49')


# --- Round-trip ---

def test_deci_roundtrip_0():
    buf = encode_decimal(Decimal('1.01'))
    print(hexdump(buf))
    assert decode_decimal(buf,0,len(buf))  == Decimal('1.01')


def test_deci_roundtrip_1():
    buf = encode_decimal(Decimal('13.37'))
    print(hexdump(buf))
    assert decode_decimal(buf,0,len(buf))  == Decimal('13.37')

def test_deci_roundtrip_2():
    buf = encode_decimal(Decimal('-0.0000000006789'))
    print(hexdump(buf))
    assert decode_decimal(buf,0,len(buf))  == Decimal('-0.0000000006789')






# --- decode benchmark experiments ---

# vs:
# python -m timeit -s "from decimal import Decimal ; a=-1234 ; b=-2"  "x = Decimal(a).scaleb(b)"
# python -m timeit -s "from decimal import Decimal ; a=-1234 ; b=-2"  "ss='%ie%i' % (a,b) ; x = Decimal(ss)"
# py2:  string 4.08 usec  scaleb 9.48 usec          # lol scaleb 2x SLOWER
# py3:  string 789 nsec   scaleb 399 nsec           # string 2x slower but diff much smaller than py2
