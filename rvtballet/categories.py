"""Element category resolution for the fast scan (no full record decode of ordinary elements).

Sources, in order: (1) the element header m_categroryId (builtin negative id, or a positive id of a
CategoryElem = sub/user category, resolved to its parent builtin); (2) the small body of the
class records that carry their own category (GStyleElem, FamilySurrogate, FamSymSurrogate; Family
via its surrogate; CategoryElem via its parent); (3) otherwise the element has no category in the
file: the bucket is named per class ("none: <Class>") so it is explained, not silent."""
NOCAT = -(1 << 62)
BODY_CAT = ("GStyleElem", "FamilySurrogate", "FamSymSurrogate")


def _sc(v, W=8):
    v = int(v); return v - (1 << (8 * W)) if v >= 1 << (8 * W - 1) else v


def resolve(cat, cls, cls_names, idarr, full, W=8):
    """cat/cls/idarr: arrays from scan (cat NOCAT or -1 = none); full: {(id, class): reduced record}.
    -> (cat array with builtin ids where resolvable, NOCAT otherwise)."""
    import numpy as np
    parent = {}; own = {}; fam_of = {}
    for (eid, c), r in full.items():
        f = r["fields"]
        if c == "CategoryElem" and f.get("m_parentCategoryId") is not None: parent[int(eid)] = _sc(f["m_parentCategoryId"], W)
        elif c in BODY_CAT and f.get("m_categoryId") is not None: own[int(eid)] = _sc(f["m_categoryId"], W)
        if c == "FamilySurrogate" and f.get("m_elemId") is not None: fam_of[int(f["m_elemId"])] = int(eid)
    def builtin(v):
        for _ in range(4):
            if v < -1: return v
            if v > 0 and v in parent: v = parent[v]
            else: return NOCAT
        return NOCAT
    out = cat.copy()
    for i in range(len(out)):
        v = int(out[i]); eid = int(idarr[i]); cn = cls_names[cls[i]] if cls[i] != 65535 else ""
        if v not in (-1, NOCAT): out[i] = builtin(v); continue
        if eid in own: out[i] = builtin(own[eid])
        elif cn == "CategoryElem" and eid in parent: out[i] = builtin(parent[eid])
        elif cn == "Family" and fam_of.get(eid) in own: out[i] = builtin(own[fam_of[eid]])
        else: out[i] = NOCAT
    return out
