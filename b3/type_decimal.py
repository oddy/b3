# Codec for python decimal.Decimal to arbitrary-precision value-and-exponent encoding.

import decimal

from six import int2byte

from b3.type_varint import encode_uvarint, decode_uvarint
from b3.utils import IntByteAt

########################################################################################################################
# Data Format Standard
########################################################################################################################

# Goal: "small numbers are small, big numbers are big"
# We call the non-exponent 'main number' the 'value'. Others call it the signficand or (sometimes wrongly-ish) mantissa.

# --- Structure ---
# [Control byte][optional exponent uvarint][value uvarint]
# Note: the value varint is allowed to be missing if its zero. We dont have a presence flag for that,
#       so the decoder uses the size of what it's given (via end-index) to determine presence.

# --- Control Byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | 0:Number   | Sign       | Expo Sign  | Ext exp(1) | exponent   | exponent   | exponent   | exponent   |
# | 1:Special  | Sign       | Nan/Inf(2) | q/s nan(3) | unused     | unused     | unused     | unused     |
# +------------+------------+------------+------------+------------+------------+------------+------------+
# (1) 0 = exponent in bottom 4 bits, 1 = exponent varint follows
# (2) 0 = NaN, 1 = Infinity
# (3) 0 = 'Quiet' NaN, 1 = 'Signalling' NaN
BIT_SPECIAL = 0x80  # 0 = Number, 1 = special
BIT_NEGATIVE = 0x40  # 0 = +ve number, 1 = -ve number
BIT_EXP_NEGA = 0x20  # 0 = +ve exponent, 1 = -ve exponent
BIT_INFINITY = 0x20  # 0 = NaN, 1 = Infinit
BIT_EXP_EXT = 0x10  # 0 = exponent is lower 4 bits of control byte, 1 = exponent is a uvarint following control byte
BIT_SNAN = 0x10  # 0 = Quiet NaN,  1 = 'Signalling' NaN
EXPONENT_BITS = 0x0F  # Lower 4 bits of control byte

# https://www.jpl.nasa.gov/edu/news/2016/3/16/how-many-decimals-of-pi-do-we-really-need/
# @ 15dp, "voyager 1 distance-radius circle circumference error is 1.5 inches"


########################################################################################################################
# Encode
########################################################################################################################

# Note: we're not supporting compact zero-value mode in the encoder.  CZV is optional for encoders so that's ok.

# In:  num - a decimal.Decimal type ONLY
# Out: bytes
def encode_decimal(num):
    if not isinstance(num, decimal.Decimal):
        raise TypeError("only accepts decimal.Decimal objects")

    sign, digits, exp = num.as_tuple()
    special = not num.is_finite()

    # --- Control bits & special values (inf, nan) ---
    bits = 0x00
    if special:  # bit 4 (0x80) : 0=number, 1=special
        bits |= BIT_SPECIAL

    if sign:  # bit 3 (0x40) : 0=+ve number, 1=-ve number
        bits |= BIT_NEGATIVE

    if special:  # bit 2 (0x20) : [special] 0=nan 1=infinity
        if num.is_infinite():
            bits |= BIT_INFINITY
    else:  # bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo
        if exp < 0:
            bits |= BIT_EXP_NEGA

    if special:  # bit 1 (0x10) : [special] 0=qnan 1=snan
        if num.is_snan():
            bits |= BIT_SNAN
        return int2byte(bits)  # *** Special only, we're done ***

    # --- Exponent ---
    exp_abs = abs(exp)

    if exp_abs > 0x0F:  # bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows
        bits |= 0x10  # exponent > 15, store it in varint
        out = [int2byte(bits), encode_uvarint(exp_abs)]
        # ^^ uv b/c exp sign already done & we're trying to be compact
    else:  # exponent =< 15, store it in low nibble
        bits |= exp_abs & 0x0F
        out = [int2byte(bits)]

    # --- Value (significand) ---
    if digits:
        value = int("".join(map(str, digits)))  # [screaming intensifies]
        if value:  # Note that 0 = no value bytes at all.
            out.append(encode_uvarint(value))

    return b"".join(out)


########################################################################################################################
# Decode
########################################################################################################################

# In:  bytes buffer, index of our start, index of next thing's start (so index of us + size of us)
# Out: a decimal.Decimal
def decode_decimal(buf, index, end):
    bits, index = IntByteAt(buf, index)

    # --- Special literals ---
    if bits & BIT_SPECIAL:
        if bits & BIT_INFINITY:  # Is infinity, not a NaN
            lit = "Inf"
        else:  # Is a NaN
            if bits & BIT_SNAN:  # Is a Signalling NaN
                lit = "sNaN"
            else:  # Is a Quiet NaN
                lit = "NaN"

        sign_lit = "%s%s" % ("-" if bits & BIT_NEGATIVE else "", lit)
        return decimal.Decimal(sign_lit)

    # --- exponent ---
    if bits & BIT_EXP_EXT:  # exponent is a varint that follows
        exp, index = decode_uvarint(buf, index)
    else:  # exponent is bottom half of bits byte
        exp = bits & EXPONENT_BITS

    # --- value ---
    if index == end:  # Note: old behaviour, deprecated (handled by zero_value_table)
        value = 0
    else:
        value, index = decode_uvarint(buf, index)

    # Note: we cant get -0 through here if we use ints and scaleb, so using strings instead for now.

    dec_str = "%s%de%s%d" % (
        "-" if bits & BIT_NEGATIVE else "",
        value,
        "-" if bits & BIT_EXP_NEGA else "",
        exp,
    )
    # print("Dec str: %r" % dec_str)
    return decimal.Decimal(dec_str)


# decimal.Decimal(-1234).scaleb(-2)  ->  Decimal('-12.34')      # using ints
# decimal.Decimal('-1234e-2')        ->  Decimal('-12.34')      # using strings
