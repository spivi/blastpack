from blastpack import ordering


def test_invert_is_inverse():
    perm = [2, 0, 1]
    inv = ordering.invert(perm)
    assert inv == [1, 2, 0]
    for pos, node in enumerate(perm):
        assert inv[node] == pos


def test_cluster_groups_by_domain_then_type():
    g = {"n": 4, "adj": [set(), set(), set(), set()],
         "meta": {"domain_of": ["B", "A", "A", "B"],
                  "type_of": ["User", "Group", "User", "User"]}}
    # sort key (domain, type, node): A/Group/1, A/User/2, B/User/0, B/User/3
    assert ordering.cluster_aware_bloodhound(g) == [1, 2, 0, 3]


def test_arbitrary_is_a_permutation():
    g = {"n": 5, "adj": [set()] * 5, "meta": {}}
    perm = ordering.arbitrary(g, 0)
    assert sorted(perm) == [0, 1, 2, 3, 4]
