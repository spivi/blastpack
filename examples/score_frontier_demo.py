"""Example: score a candidate frontier against the admin target set, in process.

Usage: python examples/score_frontier_demo.py path/to/domain.blastpack
"""
import sys

import blastpack.lib as lib
from blastpack import metrics


def main(path):
    P = lib.load(path)
    targets = [i for i, node in enumerate(P.nodes) if metrics.is_high_value(node)]
    if not targets:
        print("no high-value targets in this pack")
        return
    target_bits = P.bitset_of(targets)
    candidates = list(range(len(P.nodes)))
    scores = P.score_frontier(candidates, target_bits)
    ranked = sorted(scores, key=lambda i: scores[i], reverse=True)[:10]
    print(f"snapshot built: {P.provenance['build_timestamp']}")
    print("top candidates by marginal HVT coverage:")
    for i in ranked:
        node = P.nodes[i]
        print(f"  +{scores[i]:3d}  {node['label']}  [{node['type']}]")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: score_frontier_demo.py <pack>")
        raise SystemExit(2)
    main(sys.argv[1])
