# blastpack

Turn one SharpHound collection into a single compact, database-free blast-radius
artifact. Query it offline, rank exposure, diff two collections, and query it
in-process from an automation harness.

## Use case

In a pentest engagement you collect SharpHound once and analyze that frozen
snapshot. Because the snapshot does not change, precomputing reachability over it
is cheap and safe. `blastpack` covers four things that are awkward to get from the
live BloodHound UI:

1. **Remediation verification by diff.** Collect before and after a fix. `blastpack
   diff` reports which principals gained or lost reach and to what. Example output:
   "disabling this delegation removed 41 principals from the path to Domain Admin."
2. **Offline querying without Neo4j.** When standing up the database in a
   locked-down client environment is impractical, you can query blast radius and
   who-can-reach-an-asset from one file on your laptop.
3. **Exposure metrics for the report.** Top footholds by blast-radius size, the
   count of principals that can reach each high-value target, and the
   blast-radius size distribution, as plain numbers.
4. **A compact, shareable artifact.** The compressed reachability map is small
   enough to attach to a report and to keep many snapshots side by side for
   diffing over time.

This is a complement to BloodHound. It does not handle live or churning graphs,
and the O(V^2) build limits it to domain-sized collections on a laptop. For a
single query at small scale, a live BFS is already instant, so the reasons to use
blastpack are the diff, the offline file, the metrics, and the library API rather
than query speed.

## Install

    pip install -e .

Requires Python 3.10+. Standard library only, no runtime dependencies.

## Commands

    blastpack build <sharphound-dir> -o domain.blastpack   # load, close, compress, gate, write
    blastpack info  domain.blastpack                        # provenance + stats + compression ratio
    blastpack radius <node> domain.blastpack                # forward: what this principal can reach
    blastpack reachers <node> domain.blastpack              # reverse: who can reach this asset
    blastpack top domain.blastpack [--k 20]                 # footholds, HVT reachers, size distribution
    blastpack diff before.blastpack after.blastpack         # per-principal reach gained/removed

`<node>` accepts a SID/objectid or a display name. A display name must match
exactly one node.

## Pack format

A pack is one gzip-compressed JSON file with four parts: `version`, `provenance`,
an ordered `nodes` table, and per-node `rows`, plus `stats`. Each row is a
zero-run RLE bitset, base64-encoded; bit `i` set means node `i` is reachable.
Nodes are stored in a domain/type-grouped order so reachable bits form long zero
runs, and that ordering is recorded in the pack. Every `build` runs an equality
gate: each stored row is decoded and checked against an independent forward BFS,
and the build aborts if any row disagrees.

## Automation surface

`blastpack.lib` is a read-only library for harnesses that query in process.
Shelling out once per query is slow, so the library loads a pack and answers
queries from memory. It returns raw bitsets and integers rather than formatted
text, and it makes no decisions; the caller does.

    import blastpack.lib as lib
    P = lib.load("domain.blastpack")
    P.reach(node)                       # int bitset: what `node` reaches
    P.reach_after([a, b])               # OR of several nodes' reach
    P.covers(bitset, targets)           # how many targets a reach already hits
    P.score_frontier(cands, targets)    # marginal new-target coverage per candidate
    P.provenance                        # includes build_timestamp (snapshot age)

Bitsets are Python `int` values (arbitrary precision). Each row is decoded once on
load. Union is `|`, intersection is `&`, popcount is `int.bit_count()`.

Snapshot staleness: a pack reflects the graph at collection time. If a harness
compromises nodes during a run, the real graph gains edges the pack does not know
about, so a `reach` result is a lower bound on the changed graph. To account for
this, either rebuild the pack or track the new edges separately.
`P.provenance["build_timestamp"]` reports the snapshot's age. The library does not
present itself as live.

## Limits

- Domain-sized collections only. The closure is O(V^2+VE). `build` warns past a
  few thousand nodes and prints an estimated build time. A large forest will not
  finish on a laptop.
- No live or churning graphs. Analyze a frozen snapshot.
- No Neo4j, no network, no GUI.
- Defensive measurement only. No collection, no exploitation, no path execution,
  no move planning.

## Reference baseline

On the public GOADv2 ESSOS.local domain (331 nodes, 845 control edges), a pack
compresses to a ratio near 0.084, with a mean blast radius of about 9.2 of 331
principals and a heavy-tailed distribution. The raw export is not bundled, so
these figures are quoted as a reference rather than reproduced here.
