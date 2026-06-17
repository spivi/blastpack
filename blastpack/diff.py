"""Diff two packs by SID: per-principal reach gained and removed.

Two packs of the same domain may use different node orderings/indices, so both are
decoded to SID-keyed reachable sets before diffing — index i is not assumed to be
the same principal in both packs.
"""
from blastpack import pack as _pack


class BasisMismatchError(Exception):
    """The two packs do not share a node basis (different SID sets)."""


def reach_by_sid(pack):
    sids = [node["id"] for node in pack["nodes"]]
    out = {}
    for i, sid in enumerate(sids):
        reached = _pack.decode_pack_row(pack, i)
        out[sid] = {sids[j] for j in reached}
    return out


def diff_packs(before, after):
    sids_before = {node["id"] for node in before["nodes"]}
    sids_after = {node["id"] for node in after["nodes"]}
    if sids_before != sids_after:
        raise BasisMismatchError(
            "packs do not share a node basis; cannot diff "
            f"({len(sids_before)} vs {len(sids_after)} principals)")

    rb = reach_by_sid(before)
    ra = reach_by_sid(after)
    changed = {}
    total_added = total_removed = 0
    for sid in rb:
        added = ra[sid] - rb[sid]
        removed = rb[sid] - ra[sid]
        if added or removed:
            changed[sid] = {"added": added, "removed": removed}
            total_added += len(added)
            total_removed += len(removed)
    return {
        "changed": changed,
        "summary": {
            "principals_changed": len(changed),
            "total_reach_added": total_added,
            "total_reach_removed": total_removed,
        },
    }
