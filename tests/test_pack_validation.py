import base64
import copy
import pathlib

import pytest

from blastpack import loader, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def _valid_pack():
    g = loader.load(FIXTURE)
    return pack.build_pack(g, source_name="essos_like", build_timestamp="t")


def test_valid_pack_passes():
    p = _valid_pack()
    assert pack.validate_pack(p) is p


def test_write_read_roundtrip_validates(tmp_path):
    p = _valid_pack()
    out = tmp_path / "x.blastpack"
    pack.write_pack(p, str(out))
    # read_pack runs validate_pack internally; a clean pack must survive it
    assert pack.read_pack(str(out))["version"] == 1


def test_bad_version_rejected():
    p = _valid_pack()
    p["version"] = 99
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_nodes_not_a_list_rejected():
    p = _valid_pack()
    p["nodes"] = {"not": "a list"}
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_length_mismatch_rejected():
    p = _valid_pack()
    p["rows"] = p["rows"][:-1]
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_duplicate_node_id_rejected():
    p = _valid_pack()
    p["nodes"][1] = copy.deepcopy(p["nodes"][0])
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_non_base64_row_rejected():
    p = _valid_pack()
    p["rows"][0] = "not*base64*!!"
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_out_of_range_bit_rejected():
    # a 3-node pack whose row DECOMPRESSES to bytes with bit 15 set (>= 3).
    # The stored row is RLE-compressed, so build it through the real codec.
    from blastpack import closure
    p = _valid_pack()
    p["nodes"] = p["nodes"][:3]
    p["rows"] = p["rows"][:3]
    row = closure.compress(b"\x00\x80")  # decompresses to bit 15 set
    p["rows"][0] = base64.b64encode(row).decode()
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_missing_provenance_field_rejected():
    p = _valid_pack()
    del p["provenance"]["build_timestamp"]
    with pytest.raises(pack.PackValidationError):
        pack.validate_pack(p)


def test_structurally_valid_wrong_row_still_passes():
    # regression: b"\xff" (bits 0-7) is a structurally valid row for a pack with
    # >= 8 nodes. It is semantically wrong but only run_oracle_gate catches that;
    # validate_pack must NOT reject it (guards against over-strict validation).
    p = _valid_pack()
    assert len(p["nodes"]) >= 8
    p["rows"][0] = base64.b64encode(b"\xff").decode()
    assert pack.validate_pack(p) is p
