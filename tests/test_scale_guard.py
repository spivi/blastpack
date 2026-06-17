from blastpack import cli


def test_scale_threshold_constant():
    # the guard fires past a few thousand nodes
    assert 1000 <= cli.SCALE_WARN_NODES <= 5000


def test_no_warning_for_small_fixture(tmp_path, capsys):
    import pathlib
    fixture = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")
    cli.main(["build", fixture, "-o", str(tmp_path / "x.blastpack")])
    text = capsys.readouterr().out
    assert "WARNING" not in text  # 11 nodes is well under threshold
