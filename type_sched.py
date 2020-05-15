
import struct, zlib, time
from   collections import namedtuple
import datetime
from   pprint import pprint

from   six import PY2, int2byte

from   varint import encode_uvarint, encode_svarint


# In:  python date, time or datetime objects.
# Out: bytes

HAS = {datetime.date : (True,False), datetime.time : (False,True), datetime.datetime : (True,True) }
def encode_sched_dt(dt):
    if isinstance(dt, datetime.time):                    # ugh datetime.time doesnt have timetuple!?
        tms = namedtuple('tms','tm_hour tm_min tm_sec tm_isdst')(dt.hour, dt.minute, dt.second, -1)
    else:
        tms = dt.timetuple()

    is_date, is_time = HAS[dt.__class__]

    if hasattr(dt,'microsecond') and dt.microsecond:
        micro = dt.microsecond
    else:
        micro = 0

    offset = dt.strftime('%z')              # blank if no tzinfo
    tzname = dt.strftime('%Z')              # blank if no tzinfo

    return encode_sched(tms, is_date, is_time, offset=offset, tzname=tzname, sub_exp=6 if micro else 0, sub=micro)


# In - mandatory: time-tuple (Y/M/D H:M:S) assumed zero-filled, if date date (bool), if time data (bool),
# In - optional:  offset, tzname, subsecond exponent, and subsecond integer
#                 offset is in "-0545" string format, tzname in string format. (e.g iana)
# Out: bytes

def encode_sched(tm, is_date, is_time, offset='', tzname='', sub_exp=0, sub=0):
    # --- flags byte ---
    # +------------+------------+------------+------------+------------+------------+------------+------------+
    # | has date   | has time   | has offset | has tzname | reserved   | reserved   | sub_exp    | sub_exp    |
    # +------------+------------+------------+------------+------------+------------+------------+------------+
    flags = 0x00
    if is_date:    flags |= 0x80
    if is_time:    flags |= 0x40
    if offset:     flags |= 0x10
    if tzname:     flags |= 0x20
    flags |= ((abs(sub_exp) / 3) & 0x03)    # 0 3 6 9 only legal sub_exps.  always -ve so we dont need a sign for it.

    # --- Data bytes ---
    out = [int2byte(flags)]
    if is_date:     out.extend([encode_svarint(tm.tm_year), int2byte(tm.tm_mon), int2byte(tm.tm_mday)])
    if is_time:     out.extend([int2byte(tm.tm_hour), int2byte(tm.tm_min), int2byte(tm.tm_sec)])
    if offset:      out.append(encode_offset(offset, tm))   # dst on, vs dst off *or not present*. This may not be useful.
    if tzname:      out.append(encode_tzname(tzname))
    if sub_exp and sub:
        out.append(encode_uvarint(sub))
    # pprint(out)
    return b''.join(out)


MINUTE_BITS = {'00':0x00, '15':0x10, '30':0x20, '45':0x30}

def encode_offset(offset, tm=None):
    # --- Offset byte ---
    # +------------+------------+------------+------------+------------+------------+------------+------------+
    # | sign       | dst on     | minutes    | minutes    | hour       | hour       | hour       | hour       |
    # +------------+------------+------------+------------+------------+------------+------------+------------+
    offbyte = 0x00
    if offset[0] == "-":        offbyte |= 0x80     # sign bit
    if tm and tm.tm_isdst == 1: offbyte |= 0x40     # DST bit - 1=in DST, 0=out DST or DST not present.
    min_str = offset[3:5]
    offbyte |= (0x30 & MINUTE_BITS[min_str])    # minutes bits
    hour_str = offset[1:3]
    offbyte |= (0x0f & int(hour_str))           # hour bits
    return int2byte(offbyte)


def encode_tzname(tzname):
    if not PY2:             tzname = bytes(tzname, 'ascii')     # iana says they're ascii.
    ncrc = zlib.crc32(tzname) & 0xffffffff
    return struct.pack('<L', ncrc)

# in py3: zlib.crc32(b'America/North_Dakota/New_Salem')   but you can still do the & 0xfffff
# in py2: zlib.crc32(b'America/North_Dakota/New_Salem') & 0xffffffff  to get unsigned.
# in go: crc32.ChecksumIEEE([]byte("America/North_Dakota/New_Salem")))

########################################################################################################################
# NOTES
########################################################################################################################

# --- get dict of zones from dateutil. ---
# from dateutil.zoneinfo import get_zonefile_instance
# zonenames = list(get_zonefile_instance().zones)




# --- Date time notes ---



# The tm_isdst flag of the result is set according to the dst() method: tzinfo is None or dst() returns None, tm_isdst is set to -1;
# else if dst() returns a non-zero value, tm_isdst is set to 1; else tm_isdst is set to 0.


# Record in the offset if dst was on, *shrug* no idea if this is sufficient.

# dst: we dont have to care about it and maybe shouldnt even record it, but we will record dst ON or OFF/UNKNOWN in a bit in the offset.

# The microseconds are legit on linux. They're low-res on windows, particularly python 2.
# the "offset FROM utc"

# Policy: re- storing whether dst is in effect - 1) the future doesn't need it, it can be worked out from the given
#         TZ name and system resources at the time. and its orthogonal to someone requesting "5pm pacific auckland time" anyway.
#         2) the past may find it useful? i'm not sure? so we'll store it using that bit in the offset.
# So not storing How Much DST is a Limitation, and not storing with finer granularity than 15-minute intervals is a Limitation.
# Current research bears these limitations out.

# Never use .utcnow, because it returns the currentl UTC time but as a naive object so you can't tell if it's UTC or what.

# python (2) says "objects of the date type are always naive."  So no tzinfo, no dst.



# Note note: you take some datetimes, and perform your calculations, and the calculations e.g. move the date into a different DST, what do?
# Note note: in pytz your screwed (you have to call normalize all the time), with dateutil it does the tz calcs lazily on-access, so at the "last minute"
# Note note: dateutil has a lot of good stuff. e.g.
# "Because Windows does not have an equivalent of time.tzset(), on Windows, dateutil.tz.tzlocal instances will always
#  reflect the time zone settings //at the time that the process was started//, meaning changes to the machine's time
#  zone settings during the run of a program on Windows will not be reflected by dateutil.tz.tzlocal. Because tzwinlocal
#  reads the registry directly, it is unaffected by this issue."


# *** USE DATE UTIL NOT PYTZ ***
# dateutil.tz performs calculations lazily, only when they are needed.
# pytz performs tz-calculations when localize called, which means you have to call normalize() on all calculation outputs, to get it to *perform the calculations again*
# (because the result may be e.g in daylight savings now when it wasn't before.

# from the tz database people:
# The POSIX tzname variable does not suffice and is no longer needed. To get a timestamp's time zone abbreviation, consult the tm_zone member if available; otherwise, use strftime's "%Z" conversion specification.
