
from six import PY2
from hexdump import hexdump

from varint import encode_uvarint, decode_uvarint, encode_svarint

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


def test_uvarint_enc():
    assert encode_uvarint(50)    == SBytes("32")
    assert encode_uvarint(500)   == SBytes("f4 03")         # note: skipping 5000, its still 2 bytes
    assert encode_uvarint(50000) == SBytes("d0 86 03")

def test_uvarint_dec():
    assert decode_uvarint(SBytes("32"), 0)       == (50, 1)
    assert decode_uvarint(SBytes("f4 03"), 0)    == (500, 2)
    assert decode_uvarint(SBytes("d0 86 03"), 0) == (50000, 3)

def test_svarint_enc():
    print hexdump( encode_svarint(-49) )  #   == SBytes("32")
    print hexdump( encode_svarint(-499) ) #   == SBytes("f4 03")         # note: skipping 5000, its still 2 bytes
    print hexdump( encode_svarint(-4999) ) #   == SBytes("f4 03")         # note: skipping 5000, its still 2 bytes
    print hexdump( encode_svarint(-49999) ) # == SBytes("d0 86 03")


def test_example():
    assert True

# def test_fail():
#     assert False

