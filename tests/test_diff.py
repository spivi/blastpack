import pathlib

import pytest

from blastpack import diff, loader, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_reach_by_sid_keys_are_all_principals():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="x", build_timestamp="t")
    rbs = diff.reach_by_sid(p)
    assert set(rbs) == set(g["meta"]["sid_of"])


def test_diff_identical_packs_is_empty():
    g = loader.load(FIXTURE)
    p = pack.build_pack(g, source_name="x", build_timestamp="t")
    d = diff.diff_packs(p, p)
    assert d["changed"] == {}
    assert d["summary"]["principals_changed"] == 0


def test_diff_detects_single_edge_removal():
    # before: full fixture. after: drop ALICE -> DOMAIN ADMINS member edge.
    g_before = loader.load(FIXTURE)
    g_after = loader.load(FIXTURE)
    alice = g_after["meta"]["sid_of"].index("S-1-5-21-AAA-1001")
    da = g_after["meta"]["sid_of"].index("S-1-5-21-AAA-512")
    g_after["adj"][alice].discard(da)  # remove the controlling edge

    p_before = pack.build_pack(g_before, source_name="b", build_timestamp="t")
    p_after = pack.build_pack(g_after, source_name="a", build_timestamp="t")
    d = diff.diff_packs(p_before, p_after)

    # ALICE loses reach (everything DA reached); nobody gains anything.
    assert "S-1-5-21-AAA-1001" in d["changed"]
    assert d["changed"]["S-1-5-21-AAA-1001"]["removed"]
    for sid, ch in d["changed"].items():
        assert ch["added"] == set()  # removal-only change


def test_diff_basis_mismatch_raises():
    g = loader.load(FIXTURE)
    p_full = pack.build_pack(g, source_name="x", build_timestamp="t")
    # a pack with a different node basis: drop the last node
    p_short = pack.build_pack(g, source_name="x", build_timestamp="t")
    p_short["nodes"] = p_short["nodes"][:-1]
    p_short["rows"] = p_short["rows"][:-1]
    with pytest.raises(diff.BasisMismatchError):
        diff.diff_packs(p_full, p_short)
