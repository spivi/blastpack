"""Read-only automation surface: in-process bitset and set-algebra queries.

Each RLE row is decoded once on load into a Python int bitset (bit i set means
node i is reachable). Data and set algebra only — no planning, no next-hop
selection, no execution. The map is a snapshot: a reach answer is a lower bound
on a graph that has changed since collection. provenance exposes the build
timestamp so the caller can see the snapshot's age.
"""
from blastpack import pack as _pack


def _row_to_int(pack_dict, i):
    bits = 0
    for b in _pack.decode_pack_row(pack_dict, i):
        bits |= (1 << b)
    return bits


class Pack:
    def __init__(self, pack_dict):
        self._pack = pack_dict
        self._rows = [_row_to_int(pack_dict, i)
                      for i in range(len(pack_dict["nodes"]))]

    @property
    def nodes(self):
        return self._pack["nodes"]

    @property
    def provenance(self):
        return self._pack["provenance"]

    def resolve(self, node):
        if isinstance(node, int):
            return node
        return _pack.resolve_node(self._pack, node)

    def bitset_of(self, nodes):
        bits = 0
        for node in nodes:
            bits |= (1 << self.resolve(node))
        return bits

    def reach(self, node):
        return self._rows[self.resolve(node)]

    def reach_after(self, nodes):
        bits = 0
        for node in nodes:
            bits |= self._rows[self.resolve(node)]
        return bits

    def covers(self, bitset, targets):
        if not isinstance(targets, int):
            targets = self.bitset_of(targets)
        return (bitset & targets).bit_count()

    def score_frontier(self, candidates, targets, have=None):
        if not isinstance(targets, int):
            targets = self.bitset_of(targets)
        base = self.reach_after(have) if have else 0
        base_hits = (base & targets).bit_count()
        scores = {}
        for c in candidates:
            ci = self.resolve(c)
            combined = base | self._rows[ci]
            scores[ci] = (combined & targets).bit_count() - base_hits
        return scores


def load(path):
    return Pack(_pack.read_pack(path))
