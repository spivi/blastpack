from blastpack import metrics


def test_is_high_value_by_rid():
    assert metrics.is_high_value({"id": "S-1-5-21-AAA-512", "label": "x",
                                  "type": "Group", "highvalue": False})
    assert metrics.is_high_value({"id": "S-1-5-21-AAA-519", "label": "x",
                                  "type": "Group", "highvalue": False})
    assert metrics.is_high_value({"id": "S-1-5-21-AAA-544", "label": "x",
                                  "type": "Group", "highvalue": False})


def test_is_high_value_by_name():
    assert metrics.is_high_value({"id": "S-1-5-21-AAA-9999",
                                  "label": "ENTERPRISE ADMINS@CORP.LOCAL",
                                  "type": "Group", "highvalue": False})


def test_is_high_value_by_flag():
    assert metrics.is_high_value({"id": "S-1-5-21-AAA-9999", "label": "x",
                                  "type": "User", "highvalue": True})


def test_not_high_value():
    assert not metrics.is_high_value({"id": "S-1-5-21-AAA-1099", "label": "BOB",
                                      "type": "User", "highvalue": False})


def test_percentiles_heavy_tail():
    sizes = [0] * 90 + [50] * 9 + [300]
    pct = metrics.percentiles(sizes)
    assert pct["p50"] == 0
    assert pct["max"] == 300
    assert pct["p99"] >= pct["p50"]
