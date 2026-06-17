"""Zero-run RLE bitset codec.

Runs of zero bytes are run-length encoded: a 0x00 byte is a marker, immediately
followed by a count byte (1..255) giving the number of zero bytes. Non-zero bytes
are stored literally.
"""


def compress(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b != 0:
            out.append(b)
            i += 1
            continue
        run = 0
        while i < n and data[i] == 0 and run < 255:
            run += 1
            i += 1
        out.append(0)
        out.append(run)
    return bytes(out)


def decompress(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b != 0:
            out.append(b)
            i += 1
            continue
        if i + 1 >= n:
            raise ValueError("truncated RLE stream: zero-run marker missing its count byte")
        count = data[i + 1]
        out.extend(b"\x00" * count)
        i += 2
    return bytes(out)
