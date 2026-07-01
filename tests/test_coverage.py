import pathlib

from blastpack import loader

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")
SAMPLE = str(pathlib.Path(__file__).parent.parent / "examples" / "sample_data")


def test_sample_reports_unsupported_edges():
    g = loader.load(SAMPLE)
    uec = g["meta"]["unsupported_edge_counts"]
    assert isinstance(uec, dict)
    # the sample deliberately carries rights outside CONTROL_EDGES
    assert uec.get("AddKeyCredentialLink") == 1
    assert uec.get("SyncLAPSPassword") == 1


def test_sample_reports_unmodeled_file_category():
    g = loader.load(SAMPLE)
    uft = g["meta"]["unsupported_file_types"]
    assert uft.get("CertTemplate") == 1


def test_fully_modeled_fixture_has_no_false_positives():
    # the essos_like fixture uses only supported rights and modeled file types,
    # so both coverage maps must be empty (guards against over-counting)
    g = loader.load(FIXTURE)
    assert g["meta"]["unsupported_edge_counts"] == {}
    assert g["meta"]["unsupported_file_types"] == {}


def test_supported_right_is_not_counted_as_unsupported():
    g = loader.load(SAMPLE)
    # GenericAll IS supported; it must not leak into the unsupported map
    assert "GenericAll" not in g["meta"]["unsupported_edge_counts"]
