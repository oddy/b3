from collections import namedtuple
import datetime

from six import PY2

from b3.utils import SBytes
from b3.type_sched import encode_sched_gen, encode_sched, decode_sched, decode_offset

# Note: these test the sched CODEC directly, rather than going through Item

# --- timetuple helper ---

TMX = namedtuple("tmx", "tm_year tm_mon tm_mday tm_hour tm_min tm_sec tm_isdst")


def TmTime(hms_str):
    return TMX(*[int(i) for i in ("0 0 0 " + hms_str + " -1").split()])


def TmDate(ymd_str):
    return TMX(*[int(i) for i in (ymd_str + " 0 0 0 -1").split()])


def TmDateTime(ymdhms):
    return TMX(*[int(i) for i in (ymdhms + " -1").split()])


def test_tmfuncs():
    assert TmTime("13 37 20").tm_min == 37
    assert TmTime("13 37 20").tm_isdst == -1
    assert TmDate("2020 01 16").tm_year == 2020
    assert TmDateTime("2020 01 16 13 37 29").tm_mday == 16


# --- Testing the general-purpose encode API ---


def test_sched_gen_date_enc():
    assert encode_sched_gen(TmDate("2020 01 16"), True, False) == SBytes("80 c8 1f 01 10")
    assert encode_sched_gen(TmDate("1984 01 16"), True, False) == SBytes("80 80 1f 01 10")
    assert encode_sched_gen(TmDate("-1984 01 16"), True, False) == SBytes("80 ff 1e 01 10")


def test_enc_gen_time():
    assert encode_sched_gen(TmTime("13 37 20"), False, True) == SBytes("40 0d 25 14")
    assert encode_sched_gen(TmTime("1 1 1"), False, True) == SBytes("40 01 01 01")


def test_enc_gen_date_time():
    assert encode_sched_gen(TmDateTime("2020 01 16 13 37 20"), True, True) == SBytes(
        "c0 c8 1f 01 10 0d 25 14"
    )


def test_enc_gen_offset():
    assert encode_sched_gen(None, False, False, offset="+0200") == SBytes("20 02")
    assert encode_sched_gen(None, False, False, offset="-0200") == SBytes("20 82")
    assert encode_sched_gen(None, False, False, offset="+0215") == SBytes("20 12")
    assert encode_sched_gen(None, False, False, offset="-0230") == SBytes("20 a2")
    assert encode_sched_gen(None, False, False, offset="+0245") == SBytes("20 32")
    assert encode_sched_gen(None, False, False, offset="+1100") == SBytes("20 0b")


def test_enc_gen_offset_dst():
    assert encode_sched_gen(TMX(0, 0, 0, 0, 0, 0, 0), False, False, offset="+0200") == SBytes("20 02")
    assert encode_sched_gen(TMX(0, 0, 0, 0, 0, 0, 1), False, False, offset="+0200") == SBytes("20 42")
    assert encode_sched_gen(TMX(0, 0, 0, 0, 0, 0, -1), False, False, offset="+0200") == SBytes(
        "20 02"
    )


def test_enc_gen_tzname():
    assert encode_sched_gen(None, False, False, tzname="Pacific/Auckland") == SBytes("10 b9 f8 32 9f")
    assert encode_sched_gen(None, False, False, tzname="America/Argentina/Buenos_Aires") == SBytes(
        "10 1e 59 9d e4"
    )


def test_enc_gen_subsec():
    assert encode_sched_gen(None, False, False, sub_exp=0, sub=69) == SBytes("00")  # no sub_exp
    assert encode_sched_gen(None, False, False, sub_exp=3, sub=0) == SBytes("00")  # no sub
    assert encode_sched_gen(None, False, False, sub_exp=3, sub=69) == SBytes("01 45")  # 69 ms
    assert encode_sched_gen(None, False, False, sub_exp=-3, sub=69) == SBytes("01 45")
    # ^^ 69 ms (exponent always -ve so we dont actually need the sign)
    assert encode_sched_gen(None, False, False, sub_exp=6, sub=69) == SBytes("02 45")  # 69 us
    assert encode_sched_gen(None, False, False, sub_exp=9, sub=69) == SBytes("03 45")  # 69 ns


# --- Testing the Python Datetime encode API ---


def test_enc_dt_date():
    assert encode_sched(datetime.date(2020, 1, 16)) == SBytes("80 c8 1f 01 10")
    assert encode_sched(datetime.date(1984, 1, 16)) == SBytes("80 80 1f 01 10")
    # assert encode_sched(datetime.date(-1984, 1, 16))  == SBytes("80 ff 1e 01 10")  # python date cant do -ve years


def test_enc_dt_time():
    assert encode_sched(datetime.time(13, 37, 20)) == SBytes("40 0d 25 14")
    assert encode_sched(datetime.time(1, 1, 1)) == SBytes("40 01 01 01")


def test_enc_dt_date_time():
    assert encode_sched(datetime.datetime(2020, 1, 16, 13, 37, 20)) == SBytes(
        "c0 c8 1f 01 10 0d 25 14"
    )


def test_enc_dt_date_time_sub():
    assert encode_sched(datetime.datetime(2020, 1, 16, 13, 37, 20, 12345)) == SBytes(
        "c2 c8 1f 01 10 0d 25 14 b9 60"
    )


# --- Decode offset ---
def test_dec_gen_offset():
    assert decode_offset(SBytes("02"), 0) == ("+0200", False, 1)
    assert decode_offset(SBytes("82"), 0) == ("-0200", False, 1)
    assert decode_offset(SBytes("12"), 0) == ("+0215", False, 1)
    assert decode_offset(SBytes("a2"), 0) == ("-0230", False, 1)
    assert decode_offset(SBytes("32"), 0) == ("+0245", False, 1)
    assert decode_offset(SBytes("0b"), 0) == ("+1100", False, 1)


# --- Testing the Python Datetime decode API  ---       # Note: there is no general purpose decode API currently.


def test_dec_dt_date_time():
    assert decode_sched(SBytes("c0 c8 1f 01 10 0d 25 14"), 0, 8) == datetime.datetime(
        2020, 1, 16, 13, 37, 20
    )


def test_dec_dt_date():
    assert decode_sched(SBytes("80 c8 1f 01 10"), 0, 5) == datetime.date(2020, 1, 16)


def test_dec_dt_time():
    assert decode_sched(SBytes("40 0d 25 14"), 0, 4) == datetime.time(13, 37, 20)


def test_dec_dt_sub():
    assert decode_sched(SBytes("c2 c8 1f 01 10 0d 25 14 b9 60"), 0, 10) == datetime.datetime(
        2020, 1, 16, 13, 37, 20, 12345
    )


# Note: We can only do offsets in the stdlib in py3, py2 doesnt have a builtin concrete tzinfo class
# and we're not doing 3rd party with pytz or dateutil atm, we are waiting for py3.9 and its tz stuff

if not PY2:

    def test_dec_dt_offset():
        assert decode_sched(SBytes("e0 c8 1f 01 10 0d 25 14 a2"), 0, 9) == datetime.datetime(
            2020,
            1,
            16,
            13,
            37,
            20,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=77400)),
        )

    def test_dec_dt_offset_sub():
        assert decode_sched(SBytes("e2 c8 1f 01 10 0d 25 14 a2 b9 60"), 0, 11) == datetime.datetime(
            2020,
            1,
            16,
            13,
            37,
            20,
            12345,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=77400)),
        )

    def test_dec_dt_roundtrip():
        tzx = datetime.timezone(datetime.timedelta(days=-1, seconds=77400))
        dt_in = datetime.datetime(2020, 1, 16, 13, 37, 20, 12345, tzinfo=tzx)

        buf = encode_sched(dt_in)
        assert decode_sched(buf, 0, len(buf)) == dt_in


########################################################################################################################
# NOTES - WIP - HERE BE DRAGONS
########################################################################################################################

# --- get dict of zones from dateutil. ---
# from dateutil.zoneinfo import get_zonefile_instance
# zonenames = list(get_zonefile_instance().zones)

# 595 zones keys (olson names)
# 389 distinct tzfile entries :  len(set([i._filename for i in zones.values()]))
# [zlib.crc32(i._filename) & 0xffffffff for i in zones.values()]
# len(set(^^)) is still 389 thank fuck.

# sort the list of crc32s. yes they are all thankfully still unique.
# difference between consecutive values [j-i for i, j in zip(t[:-1], t[1:])]
# smallest is still 6991.

# Now do the abbreviated short-names.
# they're horseshit! the len(set()) is 79!

# searching the zones:
# [i for i in zones if 'lond' in i.lower()]     # 'europe/london'
# [(k,v) for k,v in zones.items() if 'GB-' in str(v)]
# The friendlynames ("olson names" e.g. Pacific/Auckland) we were hashing map N-to-1 to tznames. So there will be no way to get the olson-name.
# I suspect the olson-names are a user-input thing.
# its the ABBREVIATED tzname we get with %Z, NOT the olsen-name.

# --- To get aware datetimes using dateutil ---

# datetime.datetime.now(dateutil.tz.gettz('America/Metlakatla')).tzinfo
# datetime.datetime.now(dateutil.tz.gettz('America/Metlakatla')).tzinfo._filename   <-- datetutil only?

# strftime('%Z') is == .tzname()   "AKDT"

# so there's 3 levels of granularity -
# (3) Olson ("Pacific/Auckland") , (2) tzfilename tzfile('NZ') , (1) crappy abbreviation name "AKDT" etc.
# Paul Ganssle the smart timezone pycon (and pytz footgun) guy says never rely on the abbreviations, they're too ambiguous.

# alternatives (NON-portable):
# d.tzinfo._filename  ->  'GB-Eire', which is granularity level 2 which is ok
# we mandate sufficient granularity.

# dt.replace switches the attached timezone without touching the time numbers. 2pm LA becomes 2pm NYC.
# dt.astimezone  switches the timezone and the time numbers.  2pm LA becomes 5pm NYC.

# *** USE DATE UTIL NOT PYTZ ***
# dateutil.tz performs calculations lazily, only when they are needed.
# pytz performs tz-calculations when localize called, which means you have to call normalize() on all calculation outputs, to get it to *perform the calculations again*
# (because the result may be e.g in daylight savings now when it wasn't before.

# from the tz database people:
# The POSIX tzname variable does not suffice and is no longer needed. To get a timestamp's time zone abbreviation, consult the tm_zone member if available; otherwise, use strftime's "%Z" conversion specification.


# The tm_isdst flag of the result is set according to the dst() method: tzinfo is None or dst() returns None, tm_isdst is set to -1;
# else if dst() returns a non-zero value, tm_isdst is set to 1; else tm_isdst is set to 0.

# https://stackoverflow.com/questions/31078749/timezone-offset-sign-reversed-by-dateutil
# the sign of the offset, is it "GMT - offs = Local" or "Local + offs = GMT" ? The answer is Yes.
# the "offset FROM utc"

# The microseconds are legit on linux. They're low-res on windows, particularly python 2.

# Never use .utcnow, because it returns the currentl UTC time but as a naive object so you can't tell if it's UTC or what.

# python (2) says "objects of the date type are always naive."  So no tzinfo, no dst.

# Note note: you take some datetimes, and perform your calculations, and the calculations e.g. move the date into a different DST, what do?
# Note note: in pytz your screwed (you have to call normalize all the time), with dateutil it does the tz calcs lazily on-access, so at the "last minute"
# Note note: dateutil has a lot of good stuff. e.g.
# "Because Windows does not have an equivalent of time.tzset(), on Windows, dateutil.tz.tzlocal instances will always
#  reflect the time zone settings //at the time that the process was started//, meaning changes to the machine's time
#  zone settings during the run of a program on Windows will not be reflected by dateutil.tz.tzlocal. Because tzwinlocal
#  reads the registry directly, it is unaffected by this issue."
