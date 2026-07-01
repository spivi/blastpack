"""blastpack command-line interface."""
import argparse
import datetime
import json

from blastpack import diff as diffmod, loader, metrics, pack

SCALE_WARN_NODES = 3000

_SECURITY_PRINCIPAL_TYPES = {"User", "Group", "Computer"}


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _node_class(node):
    """'security_principal' for User/Group/Computer, else 'asset'."""
    return ("security_principal"
            if node.get("type") in _SECURITY_PRINCIPAL_TYPES else "asset")


def _node_ref(node):
    """Compact node reference for JSON output."""
    return {"id": node["id"], "label": node["label"],
            "type": node["type"], "class": _node_class(node)}


def _emit_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


def cmd_build(args):
    graph = loader.load(args.source)
    n = graph["n"]
    edges = sum(len(s) for s in graph["adj"])
    dropped = graph["meta"]["dropped_edges"]
    if n > SCALE_WARN_NODES:
        est = (n * n) / 5_000_000.0  # rough seconds estimate, O(V^2)
        print(f"WARNING: {n} nodes — build is O(V^2+VE); estimated ~{est:.0f}s. "
              f"blastpack targets domain-sized collections; a large forest will not "
              f"finish on a laptop.")
    p = pack.build_pack(graph, source_name=args.source.rstrip("/").split("/")[-1],
                        build_timestamp=_utc_now_iso())
    pack.write_pack(p, args.output)
    st = p["stats"]
    print(f"built {args.output}: nodes={n} edges={edges} dropped={dropped} "
          f"mean_reach={st['mean_reach']:.1f} ratio={st['compression_ratio']:.4f}")
    prov = p["provenance"]
    unsupported_rights = sum(prov["unsupported_edge_counts"].values())
    unmodeled_files = sum(prov["unsupported_file_types"].values())
    print(f"edge-coverage: unsupported_rights={unsupported_rights} "
          f"unmodeled_files={unmodeled_files} "
          f"(supported control-edge subset, not BloodHound-complete)")
    return 0


def cmd_info(args):
    p = pack.read_pack(args.pack)
    pr, st = p["provenance"], p["stats"]
    if args.as_json:
        return _emit_json({
            "version": p["version"],
            "ordering": p["ordering"],
            "provenance": pr,
            "stats": {k: v for k, v in st.items() if k != "reach_sizes"},
        })
    print(f"version: {p['version']}")
    print(f"source_path: {pr['source_path']}")
    print(f"collection_date: {pr['collection_date']}")
    print(f"format_version: {pr['format_version']}")
    print(f"build_timestamp: {pr['build_timestamp']}")
    print(f"ordering: {p['ordering']}")
    print(f"node_count: {pr['node_count']}  edge_count: {pr['edge_count']}  "
          f"dropped_count: {pr['dropped_count']}")
    print(f"unsupported_edge_counts: {pr['unsupported_edge_counts']}")
    print(f"unsupported_file_types: {pr['unsupported_file_types']}")
    print(f"mean_reach: {st['mean_reach']:.2f}")
    print(f"raw_bytes: {st['raw_bytes']}  compressed_bytes: {st['compressed_bytes']}  "
          f"compression_ratio: {st['compression_ratio']:.4f}")
    return 0


def reachers_of(p, target_index):
    """Indices of nodes whose blast radius contains target_index (reverse scan)."""
    out = []
    for j in range(len(p["nodes"])):
        if target_index in pack.decode_pack_row(p, j):
            out.append(j)
    return out


def cmd_radius(args):
    p = pack.read_pack(args.pack)
    try:
        i = pack.resolve_node(p, args.node)
    except pack.NodeResolveError as e:
        print(f"ERROR: {e}")
        return 2
    reached = sorted(pack.decode_pack_row(p, i))
    node = p["nodes"][i]
    if args.as_json:
        return _emit_json({
            "node": _node_ref(node),
            "reaches_count": len(reached),
            "reaches": [_node_ref(p["nodes"][idx]) for idx in reached],
        })
    print(f"{node['label']} ({node['id']}) reaches {len(reached)} nodes:")
    for idx in reached:
        r = p["nodes"][idx]
        print(f"  {r['label']}  [{r['type']}]")
    return 0


def cmd_reachers(args):
    p = pack.read_pack(args.pack)
    try:
        t = pack.resolve_node(p, args.node)
    except pack.NodeResolveError as e:
        print(f"ERROR: {e}")
        return 2
    who = reachers_of(p, t)
    node = p["nodes"][t]
    if args.as_json:
        return _emit_json({
            "node": _node_ref(node),
            "reachers_count": len(who),
            "reachers": [_node_ref(p["nodes"][idx]) for idx in who],
        })
    print(f"{len(who)} security principals can reach "
          f"{node['label']} ({node['id']}):")
    for idx in who:
        r = p["nodes"][idx]
        print(f"  {r['label']}  [{r['type']}]")
    return 0


def cmd_top(args):
    p = pack.read_pack(args.pack)
    top = metrics.top_by_radius(p, args.k)
    hv_reachers = []
    for hv in metrics.high_value_indices(p):
        count = sum(1 for j in range(len(p["nodes"]))
                    if hv in pack.decode_pack_row(p, j))
        hv_reachers.append((hv, count))
    sizes = p["stats"]["reach_sizes"]
    total = len(p["nodes"])
    pct = metrics.percentiles(sizes)
    contained = sum(1 for s in sizes if s == 0)

    if args.as_json:
        return _emit_json({
            "k": args.k,
            "top_by_radius": [
                {**_node_ref(p["nodes"][idx]), "radius": size}
                for idx, size in top],
            "reachers_per_high_value": [
                {**_node_ref(p["nodes"][hv]), "reachers": count}
                for hv, count in hv_reachers],
            "distribution": {
                "total": total, "p50": pct["p50"], "p90": pct["p90"],
                "p99": pct["p99"], "max": pct["max"], "dead_ends": contained},
        })

    print(f"Top {args.k} principals by blast-radius size:")
    for idx, size in top:
        node = p["nodes"][idx]
        print(f"  {size:5d}  {node['label']}  [{node['type']}]")

    print("\nReachers per high-value target:")
    for hv, count in hv_reachers:
        node = p["nodes"][hv]
        print(f"  {count:5d} can reach  {node['label']}  [{node['type']}]")

    print("\nHow far compromise spreads (of %d principals):" % total)
    print(f"  Typical principal reaches:   {pct['p50']} of {total}")
    print(f"  Top 10% reach at least:      {pct['p90']} of {total}")
    print(f"  Top 1% reach at least:       {pct['p99']} of {total}")
    print(f"  Worst principal reaches:     {pct['max']} of {total}")
    print(f"  Dead-end principals (reach nothing): {contained} of {total}")
    return 0


def cmd_diff(args):
    before = pack.read_pack(args.before)
    after = pack.read_pack(args.after)
    try:
        d = diffmod.diff_packs(before, after)
    except diffmod.BasisMismatchError as e:
        print(f"ERROR: {e}")
        return 2

    # label lookup by SID (use the 'after' pack's labels; bases match)
    label = {node["id"]: node["label"] for node in after["nodes"]}
    hv = {node["id"] for node in after["nodes"] if metrics.is_high_value(node)}

    s = d["summary"]
    shown = [(sid, ch) for sid, ch in
             sorted(d["changed"].items(), key=lambda kv: label.get(kv[0], kv[0]))
             if not args.focus_hv or ((ch["added"] | ch["removed"]) & hv)]

    if args.as_json:
        return _emit_json({
            "summary": s,
            "changed": [{
                "id": sid,
                "label": label.get(sid, sid),
                "added": [{"id": x, "label": label.get(x, x)}
                          for x in sorted(ch["added"], key=lambda x: label.get(x, x))],
                "removed": [{"id": x, "label": label.get(x, x)}
                            for x in sorted(ch["removed"], key=lambda x: label.get(x, x))],
            } for sid, ch in shown],
        })

    print(f"{s['principals_changed']} principals changed; "
          f"reach added={s['total_reach_added']} removed={s['total_reach_removed']}")

    for sid, ch in shown:
        print(f"\n{label.get(sid, sid)} ({sid}):")
        for s2 in sorted(ch["added"], key=lambda x: label.get(x, x)):
            print(f"  + {label.get(s2, s2)}")
        for s2 in sorted(ch["removed"], key=lambda x: label.get(x, x)):
            print(f"  - {label.get(s2, s2)}")
    return 0


def _add_json_flag(sp):
    sp.add_argument("--json", action="store_true", dest="as_json",
                    help="emit machine-readable JSON instead of human text")


def build_parser():
    p = argparse.ArgumentParser(prog="blastpack",
                                description="Compact, database-free blast-radius "
                                            "artifact from a SharpHound collection.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="load, close, compress, gate, write")
    b.add_argument("source", help="SharpHound JSON directory or .zip")
    b.add_argument("-o", "--output", required=True, help="output .blastpack path")
    b.set_defaults(func=cmd_build)

    i = sub.add_parser("info", help="provenance + stats + compression ratio")
    i.add_argument("pack", help="path to a .blastpack file")
    _add_json_flag(i)
    i.set_defaults(func=cmd_info)

    r = sub.add_parser("radius", help="forward: what this principal can reach")
    r.add_argument("node", help="SID or display name")
    r.add_argument("pack", help="path to a .blastpack file")
    _add_json_flag(r)
    r.set_defaults(func=cmd_radius)

    re = sub.add_parser("reachers", help="reverse: who can reach this asset")
    re.add_argument("node", help="SID or display name")
    re.add_argument("pack", help="path to a .blastpack file")
    _add_json_flag(re)
    re.set_defaults(func=cmd_reachers)

    t = sub.add_parser("top", help="exposure metrics: footholds, reachers, distribution")
    t.add_argument("pack", help="path to a .blastpack file")
    t.add_argument("--k", type=int, default=20, help="how many top footholds (default 20)")
    _add_json_flag(t)
    t.set_defaults(func=cmd_top)

    df = sub.add_parser("diff", help="per-principal reach gained/removed between two packs")
    df.add_argument("before", help="earlier .blastpack")
    df.add_argument("after", help="later .blastpack")
    df.add_argument("--focus-hv", action="store_true",
                    help="only changes touching a high-value target")
    _add_json_flag(df)
    df.set_defaults(func=cmd_diff)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
