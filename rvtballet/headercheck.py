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
