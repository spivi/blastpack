import pathlib

from blastpack import cli, loader, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_cli_diff_reports_only_changed_principals(tmp_path, capsys):
    before = tmp_path / "before.blastpack"
    after = tmp_path / "after.blastpack"
    cli.main(["build", FIXTURE, "-o", str(before)])

    # build an "after" pack with one edge removed, written directly
    g = loader.load(FIXTURE)
    alice = g["meta"]["sid_of"].index("S-1-5-21-AAA-1001")
    da = g["meta"]["sid_of"].index("S-1-5-21-AAA-512")
    g["adj"][alice].discard(da)
    p_after = pack.build_pack(g, source_name="after", build_timestamp="t")
    pack.write_pack(p_after, str(after))

    capsys.readouterr()
    rc = cli.main(["diff", str(before), str(after)])
    assert rc == 0
    text = capsys.readouterr().out
    assert "ALICE@CORP.LOCAL" in text          # the one principal that changed
    assert "removed" in text.lower()
    assert "BOB@CORP.LOCAL" not in text         # unchanged principal not listed


def test_cli_diff_focus_hv(tmp_path, capsys):
    before = tmp_path / "before.blastpack"
    after = tmp_path / "after.blastpack"
    cli.main(["build", FIXTURE, "-o", str(before)])
    g = loader.load(FIXTURE)
    alice = g["meta"]["sid_of"].index("S-1-5-21-AAA-1001")
    da = g["meta"]["sid_of"].index("S-1-5-21-AAA-512")
    g["adj"][alice].discard(da)
    p_after = pack.build_pack(g, source_name="after", build_timestamp="t")
    pack.write_pack(p_after, str(after))
    capsys.readouterr()
    rc = cli.main(["diff", str(before), str(after), "--focus-hv"])
    assert rc == 0


def test_cli_diff_basis_mismatch_exits_2(tmp_path, capsys):
    before = tmp_path / "before.blastpack"
    after = tmp_path / "after.blastpack"
    cli.main(["build", FIXTURE, "-o", str(before)])
    # build an after-pack with a different node basis (drop one node), write directly
    g = loader.load(FIXTURE)
    p_after = pack.build_pack(g, source_name="after", build_timestamp="t")
    p_after["nodes"] = p_after["nodes"][:-1]
    p_after["rows"] = p_after["rows"][:-1]
    pack.write_pack(p_after, str(after))
    rc = cli.main(["diff", str(before), str(after)])
    assert rc == 2
    text = capsys.readouterr().out
    assert "basis" in text.lower()
