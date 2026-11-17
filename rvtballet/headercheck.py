"""headercheck: the element header (category, owner view, family, class definition) of every EDITED element must be identical in the source and in the writer output.
c9x-rvtcat 2026-11-17: the byte-level gates accept a category change inside a declared edit; a same-length rewrite of m_categroryId (ECC/CRC valid) passed
savegate source_damage and the readback (parameters only). ~1 s per file through fastquery.classes (headers of the given ids only)."""
import os, tempfile, shutil


def _headers(buf, eids):
    from . import fastquery
    d = tempfile.mkdtemp(prefix="rvtballet-hc-")
    try:
        f = os.path.join(d, "x.rvt"); open(f, "wb").write(buf)
        return fastquery.classes(f, set(), header_ids=lambda recs: list(eids))[1]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def header_diff(src_buf, out_buf, eids):
    """-> list of messages for edited ids whose header tuple differs (or whose header vanished from the output)"""
    eids = sorted(set(eids))
    if not eids: return []
    a, b = _headers(src_buf, eids), _headers(out_buf, eids); bad = []
    for e in eids:
        if e not in a: continue      # no header in the source (reader limit): nothing to compare
        if e not in b: bad.append("element %d: header missing in the output" % e)
        elif tuple(map(str, a[e])) != tuple(map(str, b[e])): bad.append("element %d: header (category, owner view, family, class) changed %s -> %s" % (e, tuple(map(str, a[e])), tuple(map(str, b[e]))))
    return bad


def deep_diff(src_path, out_path, allowed=(), limit=20):
    """whole-model layer (opt-in, one cold scan per file, ~8 s on a 22 MB sample): the RESOLVED category (header, sub/user category parent, Family/GStyle/surrogate body), owner view,
    family and class of EVERY element must be identical in source and output, except `allowed` ids (edited, deleted, added). Catches a category rewrite in an element the ops did not name
    and in a body-level category (Family, GStyleElem) the header check cannot see. -> list of messages"""
    from . import fastinfo
    ra = fastinfo.scan(src_path, want_elements=True); rb = fastinfo.scan(out_path, want_elements=True); A, B = ra["arrays"], rb["arrays"]
    def tab(x):
        nm = x["cls_names"]
        return {int(i): (int(c), int(o), int(f), str(nm[k])) for i, c, o, f, k in zip(x["id"], x["cat"], x["owner_view"], x["family"], x["cls"])}
    fa, fb = ra.get("family_body_cats", {}), rb.get("family_body_cats", {}); extra = ["Family %d: body category (m_categoryId, live in Revit: its types take it) %d -> %d" % (e, v, fb[e]) for e, v in fa.items() if e in fb and e not in {int(x) for x in allowed} and fb[e] != v]
    a, b = tab(A), tab(B); al = {int(e) for e in allowed}; bad = []
    for e, v in a.items():
        if e in al or e not in b: continue
        if v != b[e]: bad.append("element %d: resolved (category, owner view, family, class) %s -> %s" % (e, v, b[e]))
        if len(bad) >= limit: break
    return (bad + extra)[:limit]
