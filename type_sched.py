
import struct, zlib, time
from   collections import namedtuple
import datetime
from   pprint import pprint

from   six import PY2, int2byte, byte2int

from   varint import encode_uvarint, encode_svarint, decode_uvarint, decode_svarint

########################################################################################################################
# Packing Standard
########################################################################################################################

# --- Sched Flags/Control byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | has date   | has time   | has offset | has tzname | reserved   | reserved   | sub_exp    | sub_exp    |
# +------------+------------+------------+------------+------------+------------+------------+------------+
FLAG_DATE = 0x80
FLAG_TIME = 0x40
FLAG_OFFS = 0x20
FLAG_TZNM = 0x10
SUBS_BITS = 0x03    # 0 3 6 9 are the only legal subsecond exponents.  always -ve so we dont need a sign for it.
CLS_TO_PROPS = {datetime.date: (True, False), datetime.time: (False, True), datetime.datetime: (True, True)}

# --- Shed Offset byte ---
# +------------+------------+------------+------------+------------+------------+------------+------------+
# | sign       | dst on     | minutes    | minutes    | hour       | hour       | hour       | hour       |
# +------------+------------+------------+------------+------------+------------+------------+------------+
OFFS_FLAG_SIGN   = 0x80
OFFS_FLAG_DST    = 0x40     #  1=in DST, 0=out DST or DST not present.
OFFS_MINUTE_BITS = 0x30
OFFS_MINUTE_VAL  = {'00':0x00, '15':0x10, '30':0x20, '45':0x30}     # 15-minute granularity.
OFFS_MINUTE_REV  = {v:k for k, v in OFFS_MINUTE_VAL.items()}
OFFS_HOUR_BITS   = 0x0f


########################################################################################################################
# Encode
########################################################################################################################


# In:  python date, time or datetime objects.  Optional tzname.
# Out: bytes

def encode_sched(dt, tzname=''):
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

    return encode_sched_gen(tms, is_date, is_time, offset=offset, tzname=tzname, sub_exp=6 if micro else 0, sub=micro)


# In - mandatory: time-tuple (Y/M/D H:M:S) assumed zero-filled, if date date (bool), if time data (bool),
# In - optional:  offset, tzname, subsecond exponent, and subsecond integer
#                 offset is in "-0545" string format, tzname in string format. (e.g iana)
# Out: bytes

def encode_sched_gen(tm, is_date, is_time, offset='', tzname='', sub_exp=0, sub=0):
    # --- flags byte ---
    flags = 0x00
    if is_date:    flags |= FLAG_DATE
    if is_time:    flags |= FLAG_TIME
    if offset:     flags |= FLAG_OFFS
    if tzname:     flags |= FLAG_TZNM
    if sub:        flags |= ((abs(sub_exp) // 3) & SUBS_BITS)

    # --- Data bytes ---
    out = [int2byte(flags)]
    if is_date:     out.extend([encode_svarint(tm.tm_year), int2byte(tm.tm_mon), int2byte(tm.tm_mday)])
    if is_time:     out.extend([int2byte(tm.tm_hour), int2byte(tm.tm_min), int2byte(tm.tm_sec)])  # note 24hr hour
    if offset:      out.append(encode_offset(offset, tm))   # dst on, vs dst off *or not present*. This may not be useful.
    if tzname:      out.append(encode_tzname(tzname))
    if sub_exp and sub:
        out.append(encode_uvarint(sub))

    return b''.join(out)

def encode_offset(offset, tm=None):
    offbyte = 0x00
    if offset[0] == "-":        offbyte |= OFFS_FLAG_SIGN
    if tm and tm.tm_isdst == 1: offbyte |= OFFS_FLAG_DST
    min_str = offset[3:5]
    offbyte |= (OFFS_MINUTE_BITS & OFFS_MINUTE_VAL[min_str])
    hour_str = offset[1:3]
    offbyte |= (OFFS_HOUR_BITS & int(hour_str))
    return int2byte(offbyte)


def encode_tzname(tzname):
    if not PY2:             tzname = bytes(tzname, 'ascii')     # iana says they're ascii.
    ncrc = zlib.crc32(tzname) & 0xffffffff
    return struct.pack('<L', ncrc)


########################################################################################################################
# Decode
########################################################################################################################

def IntByteAt(buf, index):
    if not PY2:
        return buf[index], index+1
    else:
        return ord(buf[index]), index+1


# Policy: we're not actually going to finish this. Try to create an aware object from the offset, but just make a tool-function
#         to deal with the incoming tzname but don't actually integrate it.

# In: buf & index of offset-byte
# Out: offset string, dst-is-on bool

def decode_offset(buf, index):                     # produce string & dst off/on bool, mirror of encode_offset
    offbyte, index = IntByteAt(buf, index)
    sign = '-' if offbyte & OFFS_FLAG_SIGN else '+'
    dst  = bool(offbyte & OFFS_FLAG_DST)
    mins = OFFS_MINUTE_REV[offbyte & OFFS_MINUTE_BITS]
    hour = '%02d' % (offbyte & OFFS_HOUR_BITS)
    return '%s%s%s' % (sign, hour, mins) , dst, index


def decode_sched(buf, index):
    year = month = day = hour = minute = second = sub = 0
    dt = None
    tzname_hash = None
    offstr = ''

    flags,index = IntByteAt(buf, index)
    is_date     = flags & 0x80
    is_time     = flags & 0x40
    is_offset   = flags & 0x20
    is_tzname   = flags & 0x10

    if flags & FLAG_DATE:
        year, index     = decode_svarint(buf, index)
        month, index    = IntByteAt(buf, index)
        day, index      = IntByteAt(buf, index)
    if flags & FLAG_TIME:
        hour, index     = IntByteAt(buf, index)
        minute, index   = IntByteAt(buf, index)
        second, index   = IntByteAt(buf, index)
    if flags & FLAG_OFFS:
        offstr,dst_on,index = decode_offset(buf, index)
    if flags & FLAG_TZNM:
        tzname_hash = struct.unpack('<L', buf[index:index+4])
        index += 4
    sub_exp     = (flags & SUBS_BITS) * 3
    if sub_exp:
        sub,index   = decode_uvarint(buf, index)

    if flags & FLAG_DATE and flags & FLAG_TIME:
        # Note: exploiting strptime %z format in py3 to parse offset & create a tzinfo'ed datetime
        if not PY2 and is_offset and offstr:
            strval = '%s %s %s %s %s %s' % (year, month, day, hour, minute, second)
            fmt = '%Y %m %d %H %M %S'
            if sub:
                strval += ' %06d' % sub
                fmt += ' %f'
            fmt += ' %z'
            strval += ' ' + offstr
            dt = datetime.datetime.strptime(strval, fmt)
        # Note: no offset and/or python2
        else:
            dt = datetime.datetime(year,month,day,hour,minute,second,sub)
    elif flags & FLAG_DATE:
        dt = datetime.date(year,month,day)
    elif flags & FLAG_TIME:
        dt = datetime.time(hour,minute,second,sub)

    return dt               # todo:   also return tzname_hash


########################################################################################################################
# Notes
########################################################################################################################

# --- Limitations ---
# * we dont store How Much DST.
# * we dont differentiate between dst off and dst-not-present.
# * granularity of offsets is 15-minute.
# Current research seems to bear these limitations out.
# * year is signed, so the standard allows for BC years, but python datetimes don't.

# --- Unfinished Things ---
# 1) any use of the dst_on flag during decode. We assume the offset is inclusive of dst at all times.
# 2) using the tzname and tzname_hash on encode and decode. (See below)
# 3) standardizing the sign of the offset. Currently it's just whatever strptime %z does.


########################################################################################################################
# TZ Name notes
########################################################################################################################

# Note: The standard enables us to efficiently serialize an optional tz name as well as the offset.
# Note: This is for e.g. medium-future event bookings if the govt changes when DST is & the time + offset is not enough info.

# --- Tzname encode ---
# The idea is to use as granular a tzname as possible. There are 3 levels of granularity:
# (3) Olson ("Europe/London") , (2) tzfilename tzfile('GB-Eire') , (1) crappy abbreviation name "NZDT" etc.
# Each one seems to be a many-to-1 from the previous.
# Paul Ganssle the smart timezone pycon (and pytz footgun) guy says never rely on the abbreviations, they're too ambiguous.

# Tried to figure out a good way to extract the best tzname from given dt objects, but it's messy, for example:
# def GranularTzName(dt):
#     tzx = dt.tzinfo
#     if not tzx:                     return ''                   # non-aware dt
#     if hasattr(tzx, 'zone'):        return tzx.zone             # pytz
#     if hasattr(tzx, '_filename'):   return tzx._filename        # dateutil.tz tzfile
#     if len(tzx.tzname) > 4:         return tzx.tzname           # windows names etc.
#     return ''                       # policy ?? send nothing if its an abbreviated name ??
#
# So we are defaulting to having it passed in to encode() as an optional named parameter.
# Note: the standard does NOT mandate lower()ing the strings.

# crc32 'hashing':
# in py2: zlib.crc32(b'America/North_Dakota/New_Salem') & 0xffffffff  to get unsigned.
# in py3: zlib.crc32(b'America/North_Dakota/New_Salem')   but you can still do the & 0xfffff
# in go: crc32.ChecksumIEEE([]byte("America/North_Dakota/New_Salem")))

# --- Tzname decode ---
# using pytz or dateutil.tz or py3.9(?):
# 1) get biggest possible list of all tznames, hash them all with crc32.
# 2) make reverse lookup table, when a hash comes in look it up, get tz entry,
# 3) and use that tz entry to get a tzinfo to
# 4) Attach to the dt / compare with given offset (if any) and pick the more appropriate one if they disagree.
#    This is THIRD PARTY stuff and we are not implementing this for now.

# Note: we cant know what the user wants re: preferring offset vs tzname at unpack-time when they clash, so we're not
#       making that choice for them, instead giving them tools to help.

# See the bottom of test_sched.py for more notes and code snippets.