
import struct, zlib, time
from   collections import namedtuple
import datetime
from   pprint import pprint

from   six import PY2, int2byte, byte2int

from   varint import encode_uvarint, encode_svarint, decode_uvarint, decode_svarint


########################################################################################################################
# Encode
########################################################################################################################

# In:  python date, time or datetime objects.  Optional tzname.
# Out: bytes

CLS_TO_PROPS = {datetime.date: (True, False), datetime.time: (False, True), datetime.datetime: (True, True)}

def encode_sched_dt(dt, tzname=''):
    if isinstance(dt, datetime.time):                    # ugh datetime.time doesnt have timetuple!?
        tms = namedtuple('tms','tm_hour tm_min tm_sec tm_isdst')(dt.hour, dt.minute, dt.second, -1)
    else:
        tms = dt.timetuple()

    is_date, is_time = CLS_TO_PROPS[dt.__class__]

    if hasattr(dt,'microsecond') and dt.microsecond:
        micro = dt.microsecond
    else:
        micro = 0

    offset = dt.strftime('%z')              # blank if no tzinfo

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
    if offset:     flags |= 0x20
    if tzname:     flags |= 0x10
    if sub:        flags |= ((abs(sub_exp) / 3) & 0x03)    # 0 3 6 9 only legal sub_exps.  always -ve so we dont need a sign for it.

    # --- Data bytes ---
    out = [int2byte(flags)]
    if is_date:     out.extend([encode_svarint(tm.tm_year), int2byte(tm.tm_mon), int2byte(tm.tm_mday)])
    if is_time:     out.extend([int2byte(tm.tm_hour), int2byte(tm.tm_min), int2byte(tm.tm_sec)])  # note 24hr hour
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
# Decode
########################################################################################################################

# Policy: we're not actually going to finish this. Try to create an aware object from the offset, but just make a tool-function
#         to deal with the incoming tzname but don't actually integrate it.

def decode_sched(buf, index):
    year=month=day=hour=minute=second=0
    flags = byte2int(buf[index])                    ;   index += 1
    is_date = flags & 0x80
    is_time = flags & 0x40
    if is_date:
        year,index  = decode_svarint(buf, index)
        month       = byte2int(buf[index])          ;   index += 1
        day         = byte2int(buf[index])          ;   index += 1
    if is_time:
        hour        = byte2int(buf[index])          ;   index += 1
        minute      = byte2int(buf[index])          ;   index += 1
        second      = byte2int(buf[index])          ;   index += 1
    if is_date and is_time:
        dt = datetime.datetime(year,month,day,hour,minute,second)
    elif is_date:
        dt = datetime.date(year,month,day)
    elif is_time:
        dt = datetime.time(hour,minute,second)

    return dt







########################################################################################################################
# Helpers
########################################################################################################################


# --- Tzname stuff ---

# Note: we cant know what the user wants re: preferring offset vs tzname at unpack-time when they clash, so we're not
#       making that choice for them, instead giving them tools to help.

# re: tzname, there's 3 levels of granularity -
# (3) Olson ("Europe/London") , (2) tzfilename tzfile('GB-Eire') , (1) crappy abbreviation name "GMT" etc.
# Each one seems to be a many-to-1 from the previous.
# Level (3) is obv fine, and (2) seems ok too, but (1) is too ambiguous, if you use that you're losing information.

# Paul Ganssle the smart timezone pycon (and pytz footgun) guy says never rely on the abbreviations, they're too ambiguous.

# Try and get a granular-as-possible tzname out of the tzinfo struct.
# do we do this property-ologically or concretely by type, given that the 2 libs that usually make these are 3rd party to begin with..
# The below is property-esque and intended as a tool for the user.

def GranularTzName(dt):
    tzx = dt.tzinfo
    if not tzx:                     return ''                   # non-aware dt
    if hasattr(tzx, 'zone'):        return tzx.zone             # pytz
    if hasattr(tzx, '_filename'):   return tzx._filename        # dateutil.tz tzfile
    if len(tzx.tzname) > 4:         return tzx.tzname           # windows names etc.

    return ''                       # note: policy: send nothing if its an abbreviated name
    # raise NotImplementedError("There is only the abbreviated tzname, what do?")


