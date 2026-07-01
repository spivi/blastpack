import json
import pathlib

from blastpack import cli, loader, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def _build(tmp_path):
    out = tmp_path / "essos.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    return str(out)


def _json_out(capsys, argv):
    capsys.readouterr()
    rc = cli.main(argv)
    assert rc == 0
    return json.loads(capsys.readouterr().out)


def test_build_json_schema(tmp_path, capsys):
    out = tmp_path / "essos.blastpack"
    d = _json_out(capsys, ["build", FIXTURE, "-o", str(out), "--json"])
    assert out.exists()
    assert d["node_count"] == 11
    assert d["bloodhound_complete"] is False
    assert d["coverage_status"] == "clean"  # essos fixture is fully modeled
    assert "unsupported_edge_counts" in d
    assert "unsupported_file_types" in d


def test_info_json_schema(tmp_path, capsys):
    path = _build(tmp_path)
    d = _json_out(capsys, ["info", "--json", path])
    assert d["version"] == 1
    assert d["ordering"] == "domain_grouped"
    assert "unsupported_edge_counts" in d["provenance"]
    assert "unsupported_file_types" in d["provenance"]
    assert "compression_ratio" in d["stats"]
    assert "reach_sizes" not in d["stats"]  # omitted from info JSON


def test_radius_json_schema(tmp_path, capsys):
    path = _build(tmp_path)
    d = _json_out(capsys, ["radius", "S-1-5-21-AAA-512", "--json", path])
    assert d["node"]["id"] == "S-1-5-21-AAA-512"
    assert d["reaches_count"] == len(d["reaches"])
    for r in d["reaches"]:
        assert set(r) == {"id", "label", "type", "class"}


def test_reachers_json_schema(tmp_path, capsys):
    path = _build(tmp_path)
    d = _json_out(capsys, ["reachers", "S-1-5-21-AAA-2001", "--json", path])
    assert d["node"]["id"] == "S-1-5-21-AAA-2001"
    assert d["reachers_count"] == len(d["reachers"])


def test_top_json_schema(tmp_path, capsys):
    path = _build(tmp_path)
    d = _json_out(capsys, ["top", "--json", path, "--k", "5"])
    assert d["k"] == 5
    assert isinstance(d["top_by_radius"], list)
    assert isinstance(d["reachers_per_high_value"], list)
    assert set(d["distribution"]) == {"total", "p50", "p90", "p99", "max", "dead_ends"}


def test_diff_json_schema(tmp_path, capsys):
    before = tmp_path / "before.blastpack"
    after = tmp_path / "after.blastpack"
    cli.main(["build", FIXTURE, "-o", str(before)])
    g = loader.load(FIXTURE)
    alice = g["meta"]["sid_of"].index("S-1-5-21-AAA-1001")
    da = g["meta"]["sid_of"].index("S-1-5-21-AAA-512")
    g["adj"][alice].discard(da)
    p_after = pack.build_pack(g, source_name="after", build_timestamp="t")
    pack.write_pack(p_after, str(after))

    d = _json_out(capsys, ["diff", str(before), str(after), "--json"])
    assert d["summary"]["principals_changed"] >= 1
    changed_ids = {c["id"] for c in d["changed"]}
    assert "S-1-5-21-AAA-1001" in changed_ids   # ALICE changed
    assert "S-1-5-21-AAA-1002" not in changed_ids  # BOB unchanged, omitted


def test_human_output_unaffected_by_json_flag(tmp_path, capsys):
    # the default (no --json) path must keep its pinned substrings
    path = _build(tmp_path)
    capsys.readouterr()
    cli.main(["info", path])
    text = capsys.readouterr().out
    assert "node_count" in text
    assert "compression_ratio" in text
