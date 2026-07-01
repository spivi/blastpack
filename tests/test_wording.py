import pathlib

from blastpack import cli

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def _build(tmp_path):
    out = tmp_path / "essos.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    return str(out)


def test_radius_counts_nodes_not_principals(tmp_path, capsys):
    path = _build(tmp_path)
    capsys.readouterr()
    cli.main(["radius", "S-1-5-21-AAA-512", path])
    text = capsys.readouterr().out
    # a radius can include computers/assets, so it counts "nodes"
    assert "nodes:" in text
    assert "principals:" not in text.splitlines()[0]


def test_reachers_are_security_principals(tmp_path, capsys):
    path = _build(tmp_path)
    capsys.readouterr()
    cli.main(["reachers", "S-1-5-21-AAA-2001", path])
    text = capsys.readouterr().out
    assert "security principals can reach" in text


def test_top_keeps_pinned_principal_phrases(tmp_path, capsys):
    path = _build(tmp_path)
    capsys.readouterr()
    cli.main(["top", path, "--k", "5"])
    text = capsys.readouterr().out
    assert "Typical principal reaches" in text
    assert "Worst principal reaches" in text
    assert "can reach" in text


def test_build_coverage_line_has_no_warning(tmp_path, capsys):
    out = tmp_path / "e.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    text = capsys.readouterr().out
    assert "edge-coverage:" in text
    assert "WARNING" not in text
