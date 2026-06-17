import pathlib

from blastpack import cli

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_top_lists_admins_and_distribution(tmp_path, capsys):
    out = tmp_path / "essos.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    capsys.readouterr()
    rc = cli.main(["top", str(out), "--k", "5"])
    assert rc == 0
    text = capsys.readouterr().out
    assert "DOMAIN ADMINS@CORP.LOCAL" in text          # admin tops radius list
    assert "Typical principal reaches" in text         # spread section
    assert "Worst principal reaches" in text           # spread section
    assert "can reach" in text                          # reachers-per-HVT section
