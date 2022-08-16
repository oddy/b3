from six import PY2

VALID_STR_TYPES = (unicode,) if PY2 else (str,)
if PY2:
    VALID_INT_TYPES = (int, long)
else:
    VALID_INT_TYPES = (int,)

# --- Bytes visualising helper ---

if PY2:

    def SBytes(hex_bytes_str):  # in: textual hexdump, out: byte-string
        return "".join([chr(int(i, 16)) for i in hex_bytes_str.split()])

else:

    def SBytes(hex_bytes_str):  # in: textual hexdump, out: byte-string
        return bytes([int(i, 16) for i in hex_bytes_str.split()])


# Like six's byte2int, but actually works, and also handles index-return.
def IntByteAt(buf, index):
    if not PY2:
        return buf[index], index + 1
    else:
        return ord(buf[index]), index + 1
