import pytest

from blastpack import rle


def test_roundtrip_empty():
    assert rle.decompress(rle.compress(b"")) == b""


def test_roundtrip_all_zeros():
    data = b"\x00" * 600  # exceeds one 255-run, exercises multi-marker
    assert rle.decompress(rle.compress(data)) == data


def test_roundtrip_mixed():
    data = b"\x00\x00\xff\x00\x01\x00\x00\x00\x80"
    assert rle.decompress(rle.compress(data)) == data


def test_zero_run_is_marker_plus_count():
    # three zeros -> 0x00 marker then count 0x03
    assert rle.compress(b"\x00\x00\x00") == b"\x00\x03"


def test_literal_bytes_passthrough():
    assert rle.compress(b"\xab\xcd") == b"\xab\xcd"


def test_decompress_truncated_marker_raises():
    with pytest.raises(ValueError):
        rle.decompress(b"\x00")  # lone zero-run marker, no count byte
