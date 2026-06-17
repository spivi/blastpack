import pathlib

from blastpack import loader

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def test_load_node_count_and_contract():
    g = loader.load(FIXTURE)
    # 4 users + 3 groups + 2 computers + 2 domains = 11
    assert g["n"] == 11
    assert len(g["adj"]) == 11
    assert all(isinstance(s, set) for s in g["adj"])


def test_meta_captures_extended_fields():
    g = loader.load(FIXTURE)
    m = g["meta"]
    for key in ("sid_of", "name_of", "type_of", "domain_of",
                "primary_group_of", "highvalue_of", "edge_counts",
                "dropped_edges", "collection", "dataset"):
        assert key in m, key
    idx = m["sid_of"].index("S-1-5-21-AAA-1001")
    assert m["name_of"][idx] == "ALICE@CORP.LOCAL"
    assert m["primary_group_of"][idx] == "S-1-5-21-AAA-513"
    # admincount true -> highvalue flag set
    assert m["highvalue_of"][idx] is True


def test_highvalue_from_property():
    g = loader.load(FIXTURE)
    m = g["meta"]
    da = m["sid_of"].index("S-1-5-21-AAA-512")  # DOMAIN ADMINS, highvalue: true
    assert m["highvalue_of"][da] is True


def test_member_edge_member_controls_group():
    g = loader.load(FIXTURE)
    m = g["meta"]
    alice = m["sid_of"].index("S-1-5-21-AAA-1001")
    da = m["sid_of"].index("S-1-5-21-AAA-512")
    assert da in g["adj"][alice]  # ALICE --MemberOf--> DOMAIN ADMINS


def test_collection_meta_picks_real_date_and_version():
    g = loader.load(FIXTURE)
    coll = g["meta"]["collection"]
    assert coll["collected_on"] == "2024-01-02T00:00:00Z"
    assert coll["format_version"] == 5
