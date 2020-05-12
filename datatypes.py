import struct, decimal, zlib, time
import six
from   six import PY2, int2byte
from   datetime import datetime
from   varint import encode_uvarint, encode_svarint

# Note: do NOT have a module named types.py. Conflicts with a stdlib .py of same name, but this only breaks on py3 for some reason.

# --- Bag end marker ---
B3_END = 0        # end marker. Always 1 byte, always \x00

# --- Structure types ---
B3_BAG = 1        # Our single multipurpose composite type, structured: [item][item][B3_END]
B3_BAG_LIST = 2   # same as BAG on wire, acts as hint to parser to yield a list-like obj where possible
B3_BAG_DICT = 3   # same as BAG on wire, acts as hint to parser to yield a dict-like obj where possible

# --- Basic types ---
B3_NULL     = 6    # None.                                                      for None.
B3_BOOL     = 5    # True or False.                                             for bool.
B3_BYTES    = 4    # List of bytes (bytearray?).           Note: str in py2.    for bytes.
B3_UTF8     = 7    # UTF8 byte strings.                    for str in py3 and unicode in py2.

# --- Funky types ---
B3_INT64    = 8    # signed 64bit integer                  faster & medium      for ints.
B3_UVARINT  = 9    # unsigned varint                       slower & small/large for ints.
B3_SVARINT  = 10   # signed varint, zigzag encoded.        slower & small/large for ints.  slightly slower than uvarint in python

B3_FLOAT64  = 10   # IEEE754 64bit signed float.           faster & medium      for floats.
B3_DECIMAL  = 11   # Arbitrary Precision decimals.         slower & compact     for decimal.

B3_STAMP64  = 13   # Signed 64bit unix ns, UTC (because unix time IS UTC)  for now-time. (ie, timestamps gotten with now() and friends) time.time()
B3_SCHED    = 14   # [some sort of]LOCAL time, offset TO utc, TZname.              for user-schedule local time. (ie, times gotten from user input, appointments and schedules.)

B3_COMPLEX = 15    # encoded as 2 float64s.


# in: some object
# out: type code or NotImplementedError

# do the compact/fast thing here.
# make it so that the Parser is fan-in only

def GuessType(obj):
    if obj is None:
        return B3_NULL

    if obj in [True, False]:
        return B3_BOOL

    if isinstance(obj, bytes):                  # Note this will catch also *str* on python2. If you want unicode out, pass unicode in.
        return B3_BYTES

    if six.PY2 and isinstance(obj, unicode):        # py2 unicode string
        return B3_UTF8

    if isinstance(obj, str):                    # Py3 unicode str only, py2 str/bytes is caught by above test.
        return B3_UTF8

    # todo: optimal selection for the types below here, depending on value, needs to be standardized.

    if isinstance(obj, int):
        if obj >= 0:    return B3_UVARINT
        else:           return B3_SVARINT
        # return B3_INT64

    if six.PY2 and isinstance(obj, long):
        return B3_SVARINT                        # the zigzag size diff is only noticeable with small numbers.

    if isinstance(obj, float):
        return B3_FLOAT64
        # return B3_BIGDEC

    if isinstance(obj, datetime):
        return B3_STAMP64
        # return B3_SCHED

    raise NotImplementedError('Unknown type %r' % type(obj))


# ---------------------------------- Decimal --------------------------------------------------------

# i say we DONT take floats if it's too hard to convert them / get the info we need out of them
# / have to get precision out of them.

# Top 4bits:
# bit 4 (0x80) : 0=number, 1=special
# bit 3 (0x40) : 0=+ve number, 1=-ve number
# bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo   [special] 0=nan 1=infinity
# bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows  [special] 0=qnan 1=snan

# Bottom 4bits:
# [number]  exponent if top bit1=0, unused otherwise
# [special] unused.

# In:  num - a decimal.Decimal type ONLY
# Out: bytes
def encode_decimal(num):
    if not isinstance(num, decimal.Decimal):
        raise TypeError("only accepts decimal.Decimal objects")

    sign,digits,exp = num.as_tuple()
    special   = not num.is_finite()

    # --- Control bits & special values (inf, nan) ---
    bits = 0x00
    if special:                                     # bit 4 (0x80) : 0=number, 1=special
        bits |= 0x80

    if sign:                                        # bit 3 (0x40) : 0=+ve number, 1=-ve number
        bits |= 0x40

    if special:                                     # bit 2 (0x20) : [special] 0=nan 1=infinity
        if num.is_infinite():
            bits |= 0x20
    else:                                           # bit 2 (0x20) : [number] 0=+ve expo 1=-ve expo
        if exp < 0:
            bits |= 0x20

    if special:                                     # bit 1 (0x10) : [special] 0=qnan 1=snan
        if num.is_snan():
            bits |= 0x10
        return int2byte(bits)                       # *** Special only, we're done ***

    # --- Exponent ---
    exp_abs   = abs(exp)

    if exp_abs > 0x0f:                              # bit 1 (0x10) : [number] 0=expo bottom-4bits 1=expo varint follows
        bits |= 0x10                                # exponent > 15, store it in varint
        out = [int2byte(bits), encode_uvarint(exp_abs)]      # uv b/c exp sign already done & we're trying to be compact
    else:                                           # exponent =< 15, store it in low nibble
        bits |= (exp_abs & 0x0f)
        out = [int2byte(bits)]

    # --- Significand ---
    if digits:
        signif = int(''.join(map(str, digits)))     # [screaming intensifies]
        if signif:                                  # Note that 0 = no signif bytes at all.
            out.append(encode_uvarint(signif))

    return b''.join(out)

# In:  bytes
# Out: a decimal.Decimal
def decode_decimal(buf):
    return None


# In:  time.time-style float.
# Note: Current policy is we're not taking datetimes for here. They get turned into SCHEDs by the auto, and if
#       the user wants to turn a datetime into a STAMP64 they have to do it themselves first.
def encode_stamp64(timestamp):
    if isinstance(timestamp, float):
        return struct.pack('d', timestamp)
    raise TypeError('STAMP64 only accepts floats, please use SCHED or convert yourself first')


# Policy: SCHED is for dates & datetimes, we dont accept a dayless python datetime.time.
#         python (2) says "objects of the date type are always naive."  So no tzinfo, no dst.

# The tm_isdst flag of the result is set according to the dst() method: tzinfo is None or dst() returns None, tm_isdst is set to -1;
# else if dst() returns a non-zero value, tm_isdst is set to 1; else tm_isdst is set to 0.

# In: a date object.

def encode_sched_date(ind):
    if not isinstance(ind, datetime.date):      raise TypeError("input must be a datetime.date")
    num = int(time.mktime(ind.timetuple()))
    return encode_sched(num, is_days=True)      # no subseconds, no tz stuff.


# The microseconds are legit on linux. They're low-res on windows, particularly python 2.

# Never use .utcnow, because it returns the currentl UTC time but as a naive object so you can't tell if it's UTC or what.


def encode_sched_datetime(indt):
    if not isinstance(indt, datetime.datetime):      raise TypeError("input must be a datetime.datetime")
    num = int(time.mktime(indt.timetuple()))
    exp = 0
    if indt.microseconds:
        num = (num * 1000000) + indt.microseconds
        exp = 6

    # now just the if tzinfo stuff and we're free. Do it tomorrow sometime.
    if indt.dst():
        dst = True
    else:
        dst = False

    offset_str = indt.strftime("%z")        # may output '' which encode_sched interprets as store no offset info


# Policy: re- storing whether dst is in effect - 1) the future doesn't need it, it can be worked out from the given
#         TZ name and system resources at the time. and its orthogonal to someone requesting "5pm pacific auckland time" anyway.
#         2) the past may find it useful? i'm not sure? so we'll store it using that bit in the offset.
# So not storing How Much DST is a Limitation, and not storing with finer granularity than 15-minute intervals is a Limitation.
# Current research bears these limitations out.


# In: whether we have date, whether we have time, offset, tzname, Y M D H M S,  subsecond exponent, and subsecond integer
#     offset is in "-0545" string format, tzname in string format. (e.g iana)
# Out: bytes

def encode_sched(has_date, has_time, offset=None, tzname=None, year=0, month=0, day=0, hour=0, minute=0, second=0, sub_exp=0, sub=0):
    # --- flags byte: presence flags for date, time, tzname, offset,  then 4 bits of sub_exp. ---
    flags = 0x00
    if has_date:    flags |= 0x80
    if has_time:    flags |= 0x40
    if offset:      flags |= 0x10
    if tzname:      flags |= 0x20
    sub_exp = abs(sub_exp)              # it's ALWAYS to the -ve so we dont actually need a sign for it.
    flags |= (sub_exp & 0x0f)           # likewise we can cram this to sec/milli/micro/nano if we need more bits.
    out = [flags]
    # --- Actual bytes for everything ---
    if has_date:    out.extend([encode_svarint(year), int2byte(month), int2byte(day)])
    if has_time:    out.extend([int2byte(hour), int2byte(minute), int2byte(second)])
    if offset:      out.append(encode_offset(offset))                                   # todo: dst ?
    if tzname:      out.append(encode_tzname(tzname))
    if sub_exp and sub:
        out.append(encode_uvarint(sub))
    return b''.join(out)

MINUTE_BITS = {'00':0x00, '15':0x10, '30':0x20, '45':0x30}

def encode_offset(offset, off_dst=False):
    offbyte = 0x00
    if offset[0] == "-":    offbyte |= 0x80     # sign bit
    if off_dst:             offbyte |= 0x40     # DST bit   (??)
    min_str = offset[3:5]
    offbyte |= (0x30 & MINUTE_BITS[min_str])    # minutes bits
    hour_str = offset[1:3]
    offbyte |= (0x0f & int(hour_str))           # hour bits
    return int2byte(offbyte)

def encode_tzname(tzname):
    if not PY2:             tzname = bytes(tzname, 'ascii')     # iana says they're ascii.
    ncrc = zlib.crc32(tzname) & 0xffffffff
    return struct.pack('<L', ncrc)





    # Note note: you take some datetimes, and perform your calculations, and the calculations e.g. move the date into a different DST, what do?
    # Note note: in pytz your screwed (you have to call normalize all the time), with dateutil it does the tz calcs lazily on-access, so at the "last minute"
    # Note note: dateutil has a lot of good stuff. e.g.
    # "Because Windows does not have an equivalent of time.tzset(), on Windows, dateutil.tz.tzlocal instances will always
    #  reflect the time zone settings //at the time that the process was started//, meaning changes to the machine's time
    #  zone settings during the run of a program on Windows will not be reflected by dateutil.tz.tzlocal. Because tzwinlocal
    #  reads the registry directly, it is unaffected by this issue."




    # d_naive = datetime.datetime.now()
    # timezone = pytz.timezone("America/Los_Angeles")
    # d_aware = timezone.localize(d_naive)

    # d = pytz.timezone("Pacific/Auckland").localize(datetime.datetime.now())           # this is the right way to use pytz, phew.

    # dateutil.tz performs calculations lazily, only when they are needed.
    # pytz performs tz-calculations when localize called, which means you have to call normalize() on all calculation outputs, to get it to *perform the calculations again*
    # (because the result may be e.g in daylight savings now when it wasn't before.




    # dnepal.strftime("%z")  -> "+0545"   from the object itself.

    # from the tz database people:
    # The POSIX tzname variable does not suffice and is no longer needed. To get a timestamp's time zone abbreviation, consult the tm_zone member if available; otherwise, use strftime's "%Z" conversion specification.

    # >>> pytz.timezone('US/Samoa').localize(datetime.datetime.now()).strftime("%z")


    # TEST: datatypes.encode_sched(44, False, -9, '+1145', 'Asia/Kathmandu' )


# when do varints jump to 3 bytes.  uvarint: 16384  svarint: 8192
# number of days is 19385



# Control byte top 4bits:
# bit 4   days-or-seconds
# bit 3   offset present
# bit 3   tzname present
# bit 1...tzname format 0=crc32, 1=something else

# Control byte bottom 4bits:
#         exponent number for arb prec main value - bc windows for example has 100-ns values

# =========
# offset byte:
# sign bit,  4bits of 12 hours, 2 bits of minutes, 1 bit for dst maybe. (still dont know about this)
# ===========
# tzname:
# 4-bytes of crc32  if control bit1=0,  othwerwise size varint followed by a string.



# YES to control byte
# 2? bits for main scale - day, sec, nano

# naive vs aware flag?  - no the presence/absence of timezone data itself indicates this

#




# utc time
# offset
# tzname


# in py3: zlib.crc32(b'America/North_Dakota/New_Salem')   but you can still do the & 0xfffff
# in py2: zlib.crc32(b'America/North_Dakota/New_Salem') & 0xffffffff  to get unsigned.
# in go: crc32.ChecksumIEEE([]byte("America/North_Dakota/New_Salem")))


# In: a python complex number object. Must have real and imag properties
def encode_complex(cplx):
    return struct.pack('dd',cplx.real,cplx.imag)

