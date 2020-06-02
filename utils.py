


from six import PY2

VALID_STR_TYPES = (unicode,) if PY2 else (str,)
if PY2:     VALID_INT_TYPES = (int, long)
else:       VALID_INT_TYPES = (int,)


# --- Bytes visualising helper ---
from six import PY2

if PY2:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return ''.join([chr(int(i,16)) for i in hex_bytes_str.split()])
else:
    def SBytes(hex_bytes_str):               # in: textual hexdump, out: byte-string
        return bytes([int(i,16) for i in hex_bytes_str.split()])


def test_utils_sbytes():
    foo = "0a 0a 40 40 64 64"
    assert SBytes(foo) == b"\x0a\x0a\x40\x40\x64\x64"
    bar = """
    64 65 66 67 68 69 70
    71 72 73 74 75 76 77
    """
    assert SBytes(bar) == b"\x64\x65\x66\x67\x68\x69\x70\x71\x72\x73\x74\x75\x76\x77"


def IntByteAt(buf, index):
    if not PY2:
        return buf[index], index+1
    else:
        return ord(buf[index]), index+1


def test_utils_byte_at():
    assert IntByteAt(b"\x07",0) == (7,1)
