# Edge support matrix

blastpack models a **supported subset** of BloodHound CE's control relationships.
This page is the authoritative boundary. It has three states:

- **Supported** — parsed and traversed; contributes to reachability.
- **Counted unsupported** — observed in the collection but *not* traversed. Every
  occurrence is tallied in `unsupported_edge_counts` (rights) or
  `unsupported_file_types` (whole file categories) and surfaced by `build`/`info`.
- **Not parsed / not observed** — blastpack does not read the source that would
  produce this edge, so it is neither traversed nor counted. These are the true
  blind spots; the sections below name them explicitly so the omission is visible
  even though the counters can't see it.

blastpack's reachability is a **lower bound relative to a complete BloodHound CE
graph**: it can only ever have fewer edges, never invented ones. It is *not*
BloodHound CE-equivalent.

## Supported (traversed)

These are the `CONTROL_EDGES` and the three collection-block edges the loader
extracts (`blastpack/loader.py`).

| Relationship | Source in the collection | Notes |
|---|---|---|
| `MemberOf` | group `Members[]` | member → group |
| `AdminTo` | computer `LocalAdmins.Results` | admin → computer |
| `HasSession` | computer `Sessions.Results` | computer → session user |
| `AdminTo` (ACE) | ACE `RightName` | if present as an ACE right |
| `GenericAll` | ACE `RightName` | full control |
| `GenericWrite` | ACE `RightName` | |
| `WriteDacl` | ACE `RightName` | |
| `WriteOwner` | ACE `RightName` | |
| `Owns` | ACE `RightName` | |
| `WriteSPN` | ACE `RightName` | |
| `ForceChangePassword` | ACE `RightName` | |
| `AddMember` / `AddMembers` / `AddSelf` | ACE `RightName` | group write |
| `AllowedToDelegate` / `AllowedToAct` | ACE `RightName` | (constrained) delegation |
| `CanRDP` / `CanPSRemote` / `ExecuteDCOM` | ACE `RightName` | remote-exec rights |
| `ReadLAPSPassword` / `ReadGMSAPassword` | ACE `RightName` | credential reads |

## Counted unsupported (observed, not traversed)

ACE `RightName` values outside `CONTROL_EDGES` are tallied in
`unsupported_edge_counts`. Whole BloodHound CE file categories the loader
recognizes by name but does not model become `unsupported_file_types`. Real
examples seen on the public GOADv2 collections (see
[sample-data-validation.md](sample-data-validation.md)):

| Right / category | Where | Why it matters |
|---|---|---|
| `Enroll` | ACE | ADCS enrollment; a component of ESC paths |
| `AllExtendedRights` | ACE | can imply `DCSync`, password resets, etc. |
| `AddKeyCredentialLink` | ACE | shadow-credentials takeover |
| `GetChanges` / `GetChangesAll` / `GetChangesInFilteredSet` | ACE | the components BloodHound post-processes into `DCSync` |
| `ManageCA` / `ManageCertificates` | ACE | ADCS CA control (ESC7) |
| `CertTemplate` files | `*certtemplates*.json` | ADCS templates (ESC1/2/3/…) |
| `EnterpriseCA` files | `*enterprisecas*.json` | issuing CAs |
| `RootCA` / `AIACA` / `NTAuthStore` files | respective JSON | PKI trust anchors |
| `IssuancePolicy` files | `*issuancepolicies*.json` | ESC13 |

## Not parsed / not observed (blind spots)

These relationships exist in BloodHound CE's traversable set but blastpack does
**not** read the source that produces them, so they are neither traversed nor
counted. This is where a "supported subset" pack differs most from a real
BloodHound graph:

- **`DCSync`** — a *post-processed* edge BloodHound derives from `GetChanges` +
  `GetChangesAll`. blastpack counts those components (above) but does not synthesize
  the `DCSync` edge.
- **ADCS ESC edges** (`ADCSESC1`, `ESC3`, `ESC4`, `ESC6a`, `ESC9a`, `ESC10a`, …) —
  derived from cert-template/CA composition. The underlying files are counted, the
  composed edges are not built.
- **`GPLink` / `WriteGPLink` / `Contains`** — GPO and OU/container linkage. OUs and
  GPOs are loaded as *nodes*, but these traversal edges are not parsed.
- **Trust edges** (`SameForestTrust`, `CrossForestTrust`, `SpoofSIDHistory`) — not
  parsed; multi-domain paths across a trust are not represented.
- **`SQLAdmin`, `HasSIDHistory`, `DumpSMSAPassword`, `SyncLAPSPassword`** and other
  specialized edges — not modeled.

## How to check coverage for a given collection

    blastpack build <source> -o out.blastpack --json

The JSON reports `unsupported_edge_counts`, `unsupported_file_types`,
`coverage_status` (`clean` / `partial`), and `bloodhound_complete: false`. A
`clean` status means no *observed* omissions; it does **not** promise BloodHound
equivalence, since the not-parsed blind spots above are invisible to the counters.
