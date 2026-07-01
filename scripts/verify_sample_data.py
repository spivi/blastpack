#!/usr/bin/env python3
"""Reproducible validation against a directory of BloodHound CE collections.

For each SharpHound/bloodhound.py .zip in the given directory, this:
  1. loads it and builds a pack (the build-time oracle gate runs automatically),
  2. INDEPENDENTLY re-verifies every stored row against a fresh forward BFS, and
  3. prints coverage counters.

"0 mismatches" means the compressed pack rows equal an independent reachability
computation over the loaded graph -- i.e. the reachability calculation is correct
over blastpack's supported edge subset. It does NOT prove the supported subset
equals BloodHound CE's traversable graph; see docs/edge-support.md.

Usage:
    python scripts/verify_sample_data.py <dir-of-zips>

Get the public sample data with:
    git clone https://github.com/m4lwhere/Bloodhound-CE-Sample-Data.git
"""
import glob
import os
import sys

from blastpack import loader, pack, oracle


def verify_one(zip_path):
    name = os.path.basename(zip_path).replace(".zip", "")
    g = loader.load(zip_path)
    p = pack.build_pack(g, source_name=name, build_timestamp="verify")

    # independent re-verification: pack row == fresh BFS, for every node
    sid_to_id = {sid: i for i, sid in enumerate(g["meta"]["sid_of"])}
    perm = [sid_to_id[n["id"]] for n in p["nodes"]]
    mismatches = 0
    for pos in range(len(p["nodes"])):
        decoded = {perm[q] for q in pack.decode_pack_row(p, pos)}
        if decoded != oracle.reachable(g, perm[pos]):
            mismatches += 1

    m = g["meta"]
    return {
        "name": name,
        "nodes": g["n"],
        "edges": sum(len(s) for s in g["adj"]),
        "dropped": m["dropped_edges"],
        "unsupported_rights": sum(m["unsupported_edge_counts"].values()),
        "unsupported_files": sum(m["unsupported_file_types"].values()),
        "mean_reach": p["stats"]["mean_reach"],
        "ratio": p["stats"]["compression_ratio"],
        "mismatches": mismatches,
    }


def main(directory):
    zips = sorted(glob.glob(os.path.join(directory, "*.zip")))
    if not zips:
        print(f"no .zip files in {directory!r}", file=sys.stderr)
        return 2

    hdr = (f"{'dataset':50} {'nodes':>6} {'edges':>6} {'drop':>6} "
           f"{'uns_rt':>7} {'uns_f':>6} {'mean':>6} {'ratio':>7} {'oracle':>8}")
    print(hdr)
    print("-" * len(hdr))
    all_ok = True
    for z in zips:
        r = verify_one(z)
        ok = r["mismatches"] == 0
        all_ok = all_ok and ok
        print(f"{r['name'][:50]:50} {r['nodes']:6d} {r['edges']:6d} "
              f"{r['dropped']:6d} {r['unsupported_rights']:7d} "
              f"{r['unsupported_files']:6d} {r['mean_reach']:6.1f} "
              f"{r['ratio']:7.4f} {'OK' if ok else str(r['mismatches']) + ' BAD':>8}")
    print()
    print("PASS: all rows match the independent oracle" if all_ok
          else "FAIL: at least one dataset had row mismatches")
    return 0 if all_ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
