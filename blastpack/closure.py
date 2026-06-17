"""Forward closure: per-source reachable set packed into an RLE-compressed bitset.

For each source we run the same directed forward flood as the oracle, pack the
reachable set into a bitset laid out in ordering space (bit at position inv[node]),
and RLE-compress it. decode_row reverses this exactly.
"""
from collections import deque

from blastpack.rle import compress, decompress
from blastpack.ordering import invert

RAW_BYTES = "raw_bytes"
COMPRESSED_BYTES = "compressed_bytes"


def _flood(adj, src):
    seen = set()
    q = deque(adj[src])
    seen.update(adj[src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    seen.discard(src)
    return seen


def _pack(reach, inv, nbytes):
    row = bytearray(nbytes)
    for node in reach:
        pos = inv[node]
        row[pos >> 3] |= (1 << (pos & 7))
    return row


def _unpack(row, perm):
    out = set()
    for byte_idx, byte in enumerate(row):
        if byte == 0:
            continue
        base = byte_idx << 3
        for bit in range(8):
            if byte & (1 << bit):
                pos = base + bit
                if pos < len(perm):
                    out.add(perm[pos])
    return out


def build(graph, perm):
    n = graph["n"]
    adj = graph["adj"]
    inv = invert(perm)
    nbytes = (n + 7) // 8
    rows = []
    raw_total = 0
    comp_total = 0
    # rows are indexed by ORDERING POSITION: rows[pos] is the node perm[pos].
    for pos in range(n):
        src = perm[pos]
        reach = _flood(adj, src)
        row = _pack(reach, inv, nbytes)
        comp = compress(bytes(row))
        rows.append(comp)
        raw_total += nbytes
        comp_total += len(comp)
    return {
        "perm": perm,
        "rows": rows,
        "nbytes": nbytes,
        RAW_BYTES: raw_total,
        COMPRESSED_BYTES: comp_total,
    }


def decode_row(table, i):
    """Original node ids reachable from the node at ordering position i."""
    row = decompress(table["rows"][i])
    return _unpack(row, table["perm"])
