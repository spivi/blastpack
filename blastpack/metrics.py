"""Exposure metrics: high-value-target detection, percentiles, top footholds."""

WELL_KNOWN_RIDS = ("-512", "-519", "-544")  # Domain Admins, Enterprise Admins, Administrators
WELL_KNOWN_NAMES = ("DOMAIN ADMINS", "ENTERPRISE ADMINS", "ADMINISTRATORS")


def is_high_value(node):
    if node.get("highvalue"):
        return True
    sid = node.get("id", "")
    if any(sid.endswith(r) for r in WELL_KNOWN_RIDS):
        return True
    label = (node.get("label") or "").upper()
    return any(name in label for name in WELL_KNOWN_NAMES)


def high_value_indices(pack):
    return [i for i, node in enumerate(pack["nodes"]) if is_high_value(node)]


def percentiles(sizes):
    if not sizes:
        return {k: 0 for k in ("p50", "p75", "p90", "p95", "p99", "max")}
    s = sorted(sizes)
    n = len(s)

    def pct(q):
        # nearest-rank percentile
        rank = max(0, min(n - 1, int(round(q / 100.0 * (n - 1)))))
        return s[rank]

    return {"p50": pct(50), "p75": pct(75), "p90": pct(90),
            "p95": pct(95), "p99": pct(99), "max": s[-1]}


def top_by_radius(pack, k):
    sizes = pack["stats"]["reach_sizes"]
    ranked = sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True)
    return [(i, sizes[i]) for i in ranked[:k]]
