# Validation against public BloodHound CE sample data

This is a reproducible run of blastpack against the public
[m4lwhere/Bloodhound-CE-Sample-Data](https://github.com/m4lwhere/Bloodhound-CE-Sample-Data)
collections — the GOADv2 ESSOS / NORTH / SEVENKINGDOMS domains, in both the
SharpHound 2.3.3 and bloodhound.py CE-branch collector formats.

## What this proves (and what it doesn't)

- **Proven:** blastpack loads real BloodHound CE v6 exports, and the compressed
  pack rows equal an **independent** forward-BFS reachability computation over the
  loaded graph — for *every* node in *every* dataset, zero mismatches. The
  reachability calculation over the supported edge subset is correct.
- **Not proven:** that blastpack's supported edge subset equals BloodHound CE's
  traversable graph. It does not — see [edge-support.md](edge-support.md). This is a
  correctness check of the computation, not a completeness check of the edge model.

## Reproduce it

    git clone https://github.com/m4lwhere/Bloodhound-CE-Sample-Data.git
    pip install -e .
    python scripts/verify_sample_data.py Bloodhound-CE-Sample-Data

`scripts/verify_sample_data.py` builds each `.zip`, then independently re-checks
every stored row against a fresh BFS oracle and prints the table below.

## Result

    dataset                                             nodes  edges   drop  uns_rt  uns_f   mean   ratio   oracle
    --------------------------------------------------------------------------------------------------------------
    ESSOS_20240410083816_BloodHound-2.3.3                 331    845      2     156      5    9.2  0.0841       OK
    NORTH_20240410083414_BloodHound-2.3.3                 320    266   1422     154      5    2.2  0.0655       OK
    SEVENKINGDOMS_20240410083609_BloodHound-2.3.3         328    887      1     149      5   10.6  0.0986       OK
    ce_branch_bloodhoundpy_essos_20240411011238_bloodh    100    373      3      53      0    9.7  0.3385       OK
    ce_branch_bloodhoundpy_north_20240411011008_bloodh     94    259    131      61      0    7.5  0.3112       OK
    ce_branch_bloodhoundpy_sevenkingdoms_2024041101105    107    433      1      56      0   11.1  0.3745       OK

    PASS: all rows match the independent oracle

Columns: `drop` = edges referencing a SID not present as a node in this collection;
`uns_rt` = unsupported ACE rights counted; `uns_f` = unmodeled file categories
counted.

## Reading the numbers

- **ESSOS SharpHound reproduces the reference baseline exactly** — 331 nodes,
  845 supported control edges, mean blast radius 9.2, compression ratio 0.084. This
  is the figure the README's "Reference baseline" section quotes; it is reproducible
  from this public data.
- **SharpHound collections show 5 unmodeled file categories each** — the ADCS/CA
  files (`rootcas`, `aiacas`, `enterprisecas`, `ntauthstores`, `certtemplates`),
  named rather than silently dropped. The CE-branch collections carry no ADCS files,
  so their `uns_f` is 0 — no false positives.
- **~150 unsupported rights per SharpHound domain** — `Enroll`, `AllExtendedRights`,
  `AddKeyCredentialLink`, and the `DCSync` components `GetChanges` / `GetChangesAll`
  are counted. These are exactly the relationships blastpack does not traverse; the
  counters make that omission visible.
- **NORTH's high `drop` (1422)** is legitimate: NORTH is a child domain in the GOAD
  forest, and many of its ACEs reference the ESSOS parent domain's Enterprise Admins
  (`…-519`) and Domain Admins (`…-512`), which are not nodes in NORTH's
  single-domain export. blastpack declines to invent nodes it never received and
  reports the count instead of guessing.

## Spot check (hand-verifiable)

On ESSOS, DAENERYS.TARGARYEN (the domain owner) has 4 direct group memberships
(Domain Admins, Administrators, Dragonsfriends, Targaryen) that transitively expand
to 326 of 331 nodes. The pack row for Daenerys equals the oracle's transitive
closure exactly, and exactly 8 principals can reach Domain Admins in both the pack
and an independent reverse-BFS. These match, which is what the aggregate
"0 mismatches" asserts for every node at once.
