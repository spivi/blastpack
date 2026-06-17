import pathlib

import pytest

from blastpack import loader, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_build_pack_passes_oracle_gate_and_has_shape():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="essos_like", build_timestamp="2026-06-17T00:00:00Z")
    assert p["version"] == 1
    assert p["ordering"] == "domain_grouped"
    assert len(p["nodes"]) == g["n"] == len(p["rows"])
    assert p["provenance"]["node_count"] == g["n"]
    assert p["provenance"]["source_path"] == "essos_like"
    assert len(p["stats"]["reach_sizes"]) == g["n"]
    # nodes are stored in ordering space; node 0's entry has the expected keys
    assert set(p["nodes"][0]) == {"id", "label", "type", "primary_group", "highvalue"}


def test_write_read_roundtrip(tmp_path):
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="essos_like", build_timestamp="t")
    out = tmp_path / "x.blastpack"
    pack.write_pack(p, str(out))
    p2 = pack.read_pack(str(out))
    assert p2["nodes"] == p["nodes"]
    assert p2["stats"]["compression_ratio"] == p["stats"]["compression_ratio"]
    # decoded rows survive the roundtrip
    for i in range(len(p["nodes"])):
        assert pack.decode_pack_row(p2, i) == pack.decode_pack_row(p, i)


def test_oracle_gate_raises_on_corrupted_row():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="essos_like", build_timestamp="t")
    # corrupt a row, then re-run the gate explicitly
    import base64
    p["rows"][0] = base64.b64encode(b"\xff").decode()
    with pytest.raises(pack.OracleGateError):
        pack.run_oracle_gate(p, g)


def test_resolve_node_by_sid_and_label():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="essos_like", build_timestamp="t")
    i = pack.resolve_node(p, "S-1-5-21-AAA-512")
    assert p["nodes"][i]["id"] == "S-1-5-21-AAA-512"
    j = pack.resolve_node(p, "domain admins@corp.local")  # case-insensitive label
    assert p["nodes"][j]["id"] == "S-1-5-21-AAA-512"


def test_resolve_node_missing_raises():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="essos_like", build_timestamp="t")
    with pytest.raises(pack.NodeResolveError):
        pack.resolve_node(p, "S-1-5-21-NOPE")
