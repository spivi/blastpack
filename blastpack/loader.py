"""Load a SharpHound (BloodHound CE) JSON export into the graph contract.

No database, no network. Maps each object's ObjectIdentifier to a contiguous
integer node id and extracts classic control edges in native source->target
direction. Emits {"n", "adj": list[set[int]], "meta"}.
"""
import json
import pathlib
import zipfile

CONTROL_EDGES = {
    "MemberOf", "AdminTo", "HasSession", "CanRDP", "CanPSRemote", "ExecuteDCOM",
    "AllowedToDelegate", "AllowedToAct", "ForceChangePassword", "AddMember",
    "AddMembers", "AddSelf", "GenericAll", "GenericWrite", "WriteDacl",
    "WriteOwner", "Owns", "WriteSPN", "ReadLAPSPassword", "ReadGMSAPassword",
}

_FILE_TYPES = {
    "users": "User", "computers": "Computer", "groups": "Group",
    "domains": "Domain", "ous": "OU", "gpos": "GPO", "containers": "Container",
}


def _iter_json_files(path):
    path = pathlib.Path(path)
    if path.is_file() and path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    yield json.loads(zf.read(name)), _type_for(name)
    else:
        for fp in sorted(path.glob("*.json")):
            yield json.loads(fp.read_text()), _type_for(fp.name)


def _type_for(filename):
    low = filename.lower()
    for frag, label in _FILE_TYPES.items():
        if frag in low:
            return label
    return "Unknown"


def _objects(doc):
    if isinstance(doc, dict):
        return doc.get("data", [])
    if isinstance(doc, list):
        return doc
    return []


def _collection_meta(docs):
    """Collection date and format version from the SharpHound meta blocks.

    Different files in one dump carry different meta; scan all of them and take
    the first that actually records each field, rather than the first non-empty
    block (which may be a file that omits them).
    """
    collected_on = None
    format_version = None
    for doc, _ in docs:
        if not isinstance(doc, dict):
            continue
        meta = doc.get("meta") or {}
        if collected_on is None and meta.get("collectedOn"):
            collected_on = meta.get("collectedOn")
        if format_version is None and meta.get("version") is not None:
            format_version = meta.get("version")
    return {"collected_on": collected_on, "format_version": format_version}


def _domain_of(obj):
    props = obj.get("Properties") or {}
    if props.get("domain"):
        return str(props["domain"]).upper()
    sid = obj.get("ObjectIdentifier", "")
    parts = sid.split("-")
    return "-".join(parts[:-1]) if len(parts) > 4 else sid


def _highvalue(props):
    if not isinstance(props, dict):
        return False
    return bool(props.get("highvalue") or props.get("admincount"))


def load(path):
    docs = list(_iter_json_files(path))
    sid_to_id = {}
    sid_of, name_of, type_of, domain_of, primary_group_of, highvalue_of = \
        [], [], [], [], [], []
    for doc, default_type in docs:
        for obj in _objects(doc):
            sid = obj.get("ObjectIdentifier")
            if not sid or sid in sid_to_id:
                continue
            sid_to_id[sid] = len(sid_of)
            props = obj.get("Properties")
            props = props if isinstance(props, dict) else {}
            sid_of.append(sid)
            name_of.append(props.get("name", sid))
            type_of.append(props.get("type", default_type))
            domain_of.append(_domain_of(obj))
            primary_group_of.append(obj.get("PrimaryGroupSID"))
            highvalue_of.append(_highvalue(props))

    n = len(sid_of)
    adj = [set() for _ in range(n)]
    edge_counts = {}
    dropped = 0

    def add_edge(src_sid, dst_sid, label):
        nonlocal dropped
        si = sid_to_id.get(src_sid)
        di = sid_to_id.get(dst_sid)
        if si is None or di is None:
            dropped += 1
            return
        if si == di:
            return
        if di not in adj[si]:
            adj[si].add(di)
            edge_counts[label] = edge_counts.get(label, 0) + 1

    for doc, _default_type in docs:
        for obj in _objects(doc):
            this_sid = obj.get("ObjectIdentifier")
            if this_sid is None:
                continue
            for ace in obj.get("Aces", []) or []:
                right = ace.get("RightName")
                if right in CONTROL_EDGES:
                    add_edge(ace.get("PrincipalSID"), this_sid, right)
            for m in obj.get("Members", []) or []:
                add_edge(m.get("ObjectIdentifier"), this_sid, "MemberOf")
            sessions = (obj.get("Sessions") or {}).get("Results", []) or []
            for s in sessions:
                add_edge(s.get("ComputerSID"), s.get("UserSID"), "HasSession")
            local_admins = (obj.get("LocalAdmins") or {}).get("Results", []) or []
            for a in local_admins:
                add_edge(a.get("ObjectIdentifier"), this_sid, "AdminTo")

    meta = {
        "sid_of": sid_of, "name_of": name_of, "type_of": type_of,
        "domain_of": domain_of, "primary_group_of": primary_group_of,
        "highvalue_of": highvalue_of, "edge_counts": edge_counts,
        "dropped_edges": dropped, "collection": _collection_meta(docs),
        "dataset": pathlib.Path(path).name,
    }
    return {"n": n, "adj": adj, "meta": meta}
