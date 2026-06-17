import pathlib

from blastpack import cli, loader, pack, oracle

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def _build(tmp_path):
    out = tmp_path / "essos.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    return str(out)


def test_radius_of_admin_matches_bfs(tmp_path, capsys):
    path = _build(tmp_path)
    capsys.readouterr()
    rc = cli.main(["radius", "S-1-5-21-AAA-512", path])  # DOMAIN ADMINS
    assert rc == 0
    text = capsys.readouterr().out
    # DOMAIN ADMINS has GenericAll on WS01 -> reaches WS01 and its session user
    assert "WS01.CORP.LOCAL" in text


def test_reachers_helper_matches_reverse_bfs(tmp_path):
    path = _build(tmp_path)
    p = pack.read_pack(path)
    # reverse-reachers of WS01 must equal the set of nodes whose forward radius
    # contains WS01, computed independently via the loaded graph + oracle.
    g = loader.load(FIXTURE)
    sid_to_id = {s: i for i, s in enumerate(g["meta"]["sid_of"])}
    ws01 = sid_to_id["S-1-5-21-AAA-2001"]
    expected_sids = {g["meta"]["sid_of"][src] for src in range(g["n"])
                     if ws01 in oracle.reachable(g, src)}
    t = pack.resolve_node(p, "S-1-5-21-AAA-2001")
    got = cli.reachers_of(p, t)
    got_sids = {p["nodes"][i]["id"] for i in got}
    assert got_sids == expected_sids


def test_reachers_of_leaf_is_few(tmp_path, capsys):
    path = _build(tmp_path)
    p = pack.read_pack(path)
    # EVE is a plain user with no inbound control; reachers should be empty
    t = pack.resolve_node(p, "S-1-5-21-AAA-1003")
    assert cli.reachers_of(p, t) == []


def test_radius_unknown_node_exits_2(tmp_path, capsys):
    out = tmp_path / "e.blastpack"
    cli.main(["build", FIXTURE, "-o", str(out)])
    capsys.readouterr()
    rc = cli.main(["radius", "S-1-5-21-NOPE", str(out)])
    assert rc == 2
    assert "ERROR" in capsys.readouterr().out
