import pathlib

from blastpack import cli

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_cli_build_then_info(tmp_path, capsys):
    out = tmp_path / "essos.blastpack"
    rc = cli.main(["build", FIXTURE, "-o", str(out)])
    assert rc == 0
    assert out.exists()
    capsys.readouterr()
    rc = cli.main(["info", str(out)])
    assert rc == 0
    text = capsys.readouterr().out
    assert "node_count" in text or "nodes" in text
    assert "compression_ratio" in text or "ratio" in text


def test_cli_build_reports_counts(tmp_path, capsys):
    out = tmp_path / "essos.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    text = capsys.readouterr().out
    assert "11" in text  # node count
