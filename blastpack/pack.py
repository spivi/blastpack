"""blastpack pack format: gzip-compressed JSON, one self-contained file.

Node index == ordering position: nodes[i] and rows[i] share index i, and bit i of
a decoded row means nodes[i] is reachable. The oracle gate re-verifies every row
against an independent forward BFS before a pack is written.
"""
import base64
import gzip
import json

from blastpack import closure, oracle
from blastpack.ordering import cluster_aware_bloodhound, invert

VERSION = 1


class OracleGateError(Exception):
    """A stored row disagreed with the independent forward-BFS reachable set."""


class NodeResolveError(Exception):
    """A node token matched zero or more than one node."""


class PackValidationError(Exception):
    """A pack failed structural validation on read, before any query."""


def build_pack(graph, ordering_name="domain_grouped", source_name="",
               build_timestamp=""):
    perm = cluster_aware_bloodhound(graph)
    table = closure.build(graph, perm)
    m = graph["meta"]

    # nodes in ordering space: index i is the node perm[i]
    nodes = []
    for pos in range(graph["n"]):
        node = perm[pos]
        nodes.append({
            "id": m["sid_of"][node],
            "label": m["name_of"][node],
            "type": m["type_of"][node],
            "primary_group": m["primary_group_of"][node],
            "highvalue": m["highvalue_of"][node],
        })

    # reach sizes and rows, ordering-indexed
    reach_sizes = []
    rows_b64 = []
    for pos in range(graph["n"]):
        reach_sizes.append(len(closure.decode_row(table, pos)))
        rows_b64.append(base64.b64encode(table["rows"][pos]).decode())

    raw = table[closure.RAW_BYTES]
    comp = table[closure.COMPRESSED_BYTES]
    edges = sum(len(s) for s in graph["adj"])
    mean_reach = sum(reach_sizes) / graph["n"] if graph["n"] else 0.0

    pack = {
        "version": VERSION,
        "provenance": {
            "source_path": source_name,
            "collection_date": m["collection"].get("collected_on"),
            "format_version": m["collection"].get("format_version"),
            "node_count": graph["n"],
            "edge_count": edges,
            "dropped_count": m["dropped_edges"],
            "build_timestamp": build_timestamp,
            "unsupported_edge_counts": m.get("unsupported_edge_counts", {}),
            "unsupported_file_types": m.get("unsupported_file_types", {}),
        },
        "ordering": ordering_name,
        "nodes": nodes,
        "rows": rows_b64,
        "stats": {
            "mean_reach": mean_reach,
            "reach_sizes": reach_sizes,
            "raw_bytes": raw,
            "compressed_bytes": comp,
            "compression_ratio": comp / raw if raw else 0.0,
        },
    }
    run_oracle_gate(pack, graph)
    return pack


def run_oracle_gate(pack, graph):
    """Decode every stored row, assert it equals the independent forward BFS.

    graph is in original-node space; the pack is in ordering space. We map each
    ordering position back to its original node via the SID table.
    """
    sid_to_id = {sid: i for i, sid in enumerate(graph["meta"]["sid_of"])}
    perm = [sid_to_id[node["id"]] for node in pack["nodes"]]
    for pos in range(len(pack["nodes"])):
        decoded_positions = decode_pack_row(pack, pos)
        decoded_nodes = {perm[p] for p in decoded_positions}
        if decoded_nodes != oracle.reachable(graph, perm[pos]):
            raise OracleGateError(
                f"row {pos} ({pack['nodes'][pos]['id']}) != forward BFS")


def decode_pack_row(pack, i):
    """Set of node INDICES reachable from node i (bits set in row i)."""
    raw = closure.decompress(base64.b64decode(pack["rows"][i]))
    out = set()
    for byte_idx, byte in enumerate(raw):
        if byte == 0:
            continue
        base = byte_idx << 3
        for bit in range(8):
            if byte & (1 << bit):
                pos = base + bit
                if pos < len(pack["nodes"]):
                    out.add(pos)
    return out


def write_pack(pack, path):
    data = json.dumps(pack, separators=(",", ":")).encode()
    with gzip.open(path, "wb") as f:
        f.write(data)


def validate_pack(pack):
    """Structural gate for read_pack: shape and decodability only, not
    reachability correctness (that is run_oracle_gate, at build time). A row that
    decodes cleanly but is semantically wrong passes here by design. Returns the
    pack so callers can validate-and-return in one line."""
    if not isinstance(pack, dict):
        raise PackValidationError("pack is not a JSON object")
    if pack.get("version") != VERSION:
        raise PackValidationError(
            f"unsupported pack version {pack.get('version')!r}; expected {VERSION}")

    nodes = pack.get("nodes")
    rows = pack.get("rows")
    if not isinstance(nodes, list):
        raise PackValidationError("nodes is not a list")
    if not isinstance(rows, list):
        raise PackValidationError("rows is not a list")
    if len(nodes) != len(rows):
        raise PackValidationError(
            f"nodes/rows length mismatch: {len(nodes)} vs {len(rows)}")

    n = len(nodes)
    seen_ids = set()
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict) or "id" not in node:
            raise PackValidationError(f"node {idx} missing 'id'")
        nid = node["id"]
        if nid in seen_ids:
            raise PackValidationError(f"duplicate node id {nid!r}")
        seen_ids.add(nid)

    for idx, row_b64 in enumerate(rows):
        if not isinstance(row_b64, str):
            raise PackValidationError(f"row {idx} is not a base64 string")
        try:
            raw = closure.decompress(base64.b64decode(row_b64, validate=True))
        except Exception as e:
            raise PackValidationError(f"row {idx} not decodable: {e}") from e
        # Byte-length overshoot alone is fine (rows are ceil(n/8) bytes); only an
        # actually-set bit at position >= n is a defect. Mirrors decode_pack_row's
        # own pos < len(nodes) guard.
        for byte_idx, byte in enumerate(raw):
            if not byte:
                continue
            for bit in range(8):
                if byte & (1 << bit) and (byte_idx * 8 + bit) >= n:
                    raise PackValidationError(
                        f"row {idx} sets bit {byte_idx * 8 + bit} >= node count {n}")

    prov = pack.get("provenance")
    if not isinstance(prov, dict):
        raise PackValidationError("provenance missing or not an object")
    for field in ("node_count", "edge_count", "build_timestamp"):
        if field not in prov:
            raise PackValidationError(f"provenance missing field {field!r}")
    return pack


def read_pack(path):
    with gzip.open(path, "rb") as f:
        pack = json.loads(f.read().decode())
    return validate_pack(pack)


def resolve_node(pack, token):
    for i, node in enumerate(pack["nodes"]):
        if node["id"] == token:
            return i
    low = token.lower()
    matches = [i for i, node in enumerate(pack["nodes"])
               if node["label"].lower() == low]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise NodeResolveError(f"no node matches {token!r}")
    cands = ", ".join(f"{pack['nodes'][i]['label']} ({pack['nodes'][i]['id']})"
                      for i in matches)
    raise NodeResolveError(f"{token!r} is ambiguous; disambiguate by SID: {cands}")
