
from six import PY2

if PY2:
    def StrBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return ''.join([chr(int(i,16)) for i in hex_bytes_str.split()])
else:
    def StrBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return bytes([int(i,16) for i in hex_bytes_str.split()])


def test_strbytes():
    foo = "0a 0a 40 40 64 64"
    assert StrBytes(foo) == b"\x0a\x0a\x40\x40\x64\x64"
    bar = """
    64 65 66 67 68 69 70
    71 72 73 74 75 76 77
    """
    assert StrBytes(bar) == b"\x64\x65\x66\x67\x68\x69\x70\x71\x72\x73\x74\x75\x76\x77"


def test_example():
    assert True

# def test_fail():
#     assert False

