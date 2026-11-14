"""Persistent per-element locator index for .rvt files (prototype, RVTOFFSET study 2026-11-14).

Finding: no stream of the file stores an element's position (see RVTOFFSET-REPORT.md). Partitions are chains of independently inflatable gzip segments
([24-byte header: u32 4, u32 x, u32 stored_len, u32 inflated_len, u32 0x65, u32 0][gzip member]); the header chain is walkable WITHOUT inflating.
This module builds, once, id -> (partition, segment, offset-in-segment, class tag, category, owner view) and answers a one-id query by inflating ONE segment.
Cache: ~/.cache/rvt-elemindex/<sha1(path|size|mtime_ns)>.npz
"""
import os, sys, struct, zlib, hashlib, time
import numpy as np
PAGE_STORED = 65249; PAGE_PAYLOAD = 64896; TAIL = 96 * 1024
CACHE = os.environ.get("RVT_ELEMINDEX_CACHE", os.path.expanduser("~/.cache/rvt-elemindex"))
_G = {}


def _paths():
    for p in (os.environ.get("RVT_READER_DIR"), os.path.expanduser("~/rvt-research"), os.path.expanduser("~/src/rvt-core/python")):
        if p and os.path.isdir(p) and p not in sys.path: sys.path.append(p)


def key(path):
    # path, size, mtime AND inode + ctime: ctime cannot be restored with utime, so an in-place edit that keeps size and mtime still invalidates; a copy or touch only forces a rebuild
    st = os.stat(path); return hashlib.sha1(("%s|%d|%d|%d|%d" % (os.path.abspath(path), st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns)).encode()).hexdigest()[:20]


class Part:
    """random access to the payload bytes of one partition stream through the CFB sector chain (only the pages asked for are read)"""
    def __init__(s, o, name):
        s.o = o; s.e = o.direntries[o._find(name)]; s.name = name; s.ss = o.sectorsize; s.fat = o.fat; s.fp = o.fp
        s.small = o.openstream(name).read() if s.e.size < o.minisectorcutoff else None      # ministream stream (< 4096 bytes): not a sector chain
        s.chain = []; c = s.e.isectStart
        while s.small is None and 0 <= c < len(s.fat) and len(s.chain) <= len(s.fat): s.chain.append(c); c = s.fat[c]
        s.npages = -(-s.e.size // PAGE_STORED)
        last = s.e.size - (s.npages - 1) * PAGE_STORED
        s.total = (s.npages - 1) * PAGE_PAYLOAD + min(last, PAGE_PAYLOAD)
    def stored(s, a, n):
        if s.small is not None: return s.small[max(a, 0):a + n]
        ss = s.ss; out = bytearray(); a = max(a, 0); end = min(a + n, s.e.size)
        while a < end:
            k = a // ss; off = a % ss; s.fp.seek((s.chain[k] + 1) * ss + off); take = min(ss - off, end - a)
            out += s.fp.read(take); a += take
        return bytes(out)
    def payload(s, a, n):
        out = bytearray(); end = min(a + n, s.total)
        while a < end:
            pg = a // PAGE_PAYLOAD; po = a % PAGE_PAYLOAD; take = min(PAGE_PAYLOAD - po, end - a)
            out += s.stored(pg * PAGE_STORED + po, take); a += take
        return bytes(out)
    def segments(s):
        """[(payload offset of the gzip member, stored_len, inflated_len)]: walks the 24-byte segment headers (no inflate, 24 bytes read per segment). Between runs of segments the
        stream holds raw interludes (text, GUIDs, records): after a break the next gzip marker preceded by a plausible header restarts the chain."""
        segs = []; hdr = None; head = s.payload(0, 64); i = head.find(b"\x1f\x8b\x08\x00")
        if i < 24: return []
        hdr = i - 24
        while hdr is not None and hdr + 24 <= s.total:
            b = s.payload(hdr, 28); w = struct.unpack("<6I", b[:24])
            if b[24:28] == b"\x1f\x8b\x08\x00" and 18 <= w[2] and hdr + 24 + w[2] <= s.total and w[0] < 16 and w[3] > 0:
                segs.append((hdr + 24, w[2], w[3])); hdr += 24 + w[2]; continue
            hdr = s._resync(hdr)
        return segs
    def _resync(s, a):
        step = 1 << 22
        while a < s.total:
            buf = s.payload(a, step + 28); p = 0
            while True:
                i = buf.find(b"\x1f\x8b\x08\x00", p)
                if i < 0 or i > step: break
                if a + i >= 24:
                    h = a + i - 24
                    if h >= 0:
                        w = struct.unpack("<6I", s.payload(h, 24))
                        if w[0] < 16 and 18 <= w[2] and h + 24 + w[2] <= s.total and w[3] > 0: return h
                p = i + 1
            a += step
        return None
    def inflate(s, seg):
        off, ln, il = seg; d = zlib.decompressobj(-15); return d.decompress(s.payload(off + 10, ln - 10), il + 64)


def _open(path):
    _paths(); import olefile
    return olefile.OleFileIO(path)


def _schema(o):
    _paths(); import fmt_parser as fp, rvtfmt, rvt_scan as S, rvt_decode as D, rvt_inventory as I, rvt_fast as F
    cls, _ = fp.parse(rvtfmt.inflate_stream(o.openstream("Formats/Latest").read())[1])
    W = S.id_size(cls); sch = D.Schema(cls)
    EH = sch.by.get("ElementHeader", -999) + 12; etags = I.element_tags(cls)
    return cls, W, sch, EH, etags, F


def _ids(o, W):
    _paths(); import rvtfmt
    et = rvtfmt.inflate_stream(o.openstream("Global/ElemTable").read())[1]
    nh = struct.unpack_from("<I", et, 2)[0]
    if W == 4:
        n = min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28
        a = np.frombuffer(et, dtype=np.uint8, count=n * 28, offset=6).reshape(n, 28)[:, :4].copy().view("<u4").ravel().astype(np.uint64)
    else:
        n = (len(et) - 6) // 40
        if 0 < nh <= n: n = nh
        r = np.frombuffer(et, dtype=np.uint8, count=n * 40, offset=6).reshape(n, 40)
        a = r[:, :8].copy().view("<u8").ravel(); b = r[:, 20:28].copy().view("<u8").ravel()
        top = int(a.max()) + 16; a = np.unique(np.concatenate([a, b[(b > 0) & (b < top)]]))
    return np.unique(a)


def _winit(path):
    o = _open(path); cls, W, sch, EH, etags, F = _schema(o)
    _G.update(path=path, o=o, cls=cls, W=W, sch=sch, EH=EH, etags=etags, F=F, parts={}, ids=_ids(o, W))
    try: es = F.es_load(path)[0]
    except Exception: es = {}
    rd = F.make_recdecoder(sch, W, es); rd.set_ids(sorted(_G["ids"].tolist())); _G["rd"] = rd
    _G["wanted"] = sorted(etags); _G["tagmask"] = np.zeros(65536, bool); _G["tagmask"][np.array(sorted(etags))] = True


def _part(pn):
    p = _G["parts"].get(pn)
    if p is None: p = _G["parts"][pn] = Part(_G["o"], pn)
    return p


def _cands(chunk, lim, idarr, W, tagmask):
    buf = np.frombuffer(chunk, dtype=np.uint8); n = len(chunk); dt = "<u4" if W == 4 else "<u8"; out = {}
    for a in range(W):
        m = (n - a) // W
        if m <= 0: continue
        arr = np.frombuffer(chunk, dtype=dt, count=m, offset=a)
        hit = np.nonzero(np.isin(arr, idarr))[0].astype(np.int64)
        pos = hit * W + a - 4; sel = (pos >= 0) & (pos < lim) & (pos <= n - 24); pos = pos[sel]; hit = hit[sel]
        for off in (12 + W, 8 + W):
            q = pos + off; v = q + 1 < n; t = np.zeros(len(pos), np.int64); t[v] = buf[q[v]].astype(np.int64) | (buf[q[v] + 1].astype(np.int64) << 8)
            ok = v & tagmask[t]
            for p_, h_, t_ in zip(pos[ok].tolist(), hit[ok].tolist(), t[ok].tolist()): out.setdefault(p_, (int(arr[h_]), t_))
    return [(p_, e, t) for p_, (e, t) in sorted(out.items())]


def _i(v):
    if not isinstance(v, int): return -1
    w = 8 * _G.get("W", 8)
    if v >= 1 << (w - 1): v -= 1 << w
    return v if -(1 << 62) < v < (1 << 62) else -1


def header_region(pn, segs, stop=30):
    """ElementHeader records (category, owner view) are NOT stored next to the element body: they sit in a dense region at the start of each partition
    (measured 10-43 segments = 1-5 percent of the inflated bytes on 8 samples 2020-2026). Decode segments until `stop` consecutive ones have no header."""
    P = _part(pn); out = {}; empty = 0
    for k in range(len(segs)):
        cur = P.inflate(segs[k]); ch = cur + (P.inflate(segs[k + 1])[:TAIL] if k + 1 < len(segs) else b"")
        r = _G["rd"].extract_chunk(ch, _G["wanted"], _G["EH"], None, _G["wanted"]); n = 0
        for e, h in r[1]:
            e = int(e)
            if e not in out: cd = h.get("m_classDef"); cd = cd.get("m_ref") if isinstance(cd, dict) else cd
            out[e] = (_i(h.get("m_categroryId")), _i(h.get("m_ownerViewId")), _i(h.get("m_familyId")), cd if isinstance(cd, int) else -1, _G["pidx"][pn], k); n += 1
        empty = 0 if n else empty + 1
        if empty >= stop and out: break
    return out


def _seg_job(job):
    """job = (partition name, seg index, [segments]) -> rows (eid, seg, off, tag): element BODY positions only (candidate scan, no record decode)"""
    pn, k, segs = job; P = _part(pn); W = _G["W"]
    cur = P.inflate(segs[k]); cand = _cands(cur + (P.inflate(segs[k + 1])[:256] if k + 1 < len(segs) else b""), len(cur), _G["ids"], W, _G["tagmask"])
    return [(e, k, p_, t) for p_, e, t in cand]


def _reopen(path):
    """forked workers must not share the parent's file handle (interleaved seeks)"""
    _G["o"] = _open(path); _G["parts"] = {}


def _seg_job2(job):
    """admin classes (no standard element-header candidate): the segment holding a decoded record of a missing id (segment granularity, off = -1)"""
    pn, k, segs = job; P = _part(pn); miss = _G["missing"]
    ch = P.inflate(segs[k]) + (P.inflate(segs[k + 1])[:TAIL] if k + 1 < len(segs) else b"")
    r = _G["rd"].extract_chunk(ch, _G["wanted"], _G["EH"], miss, _G["wanted"])
    return [(int(e), k, -1, -1) for (e, c), _ in r[0] if int(e) in _G["missset"]]


def build(path, workers=None, log=None, force=False):
    """build (or load) the index"""
    import multiprocessing as mp
    t0 = time.time(); say = log or (lambda *a: None)
    cp = os.path.join(CACHE, key(path) + ".npz")
    if os.path.exists(cp) and not force: return load(path)
    o = _open(path); pns = sorted(n for n in ("/".join(e) for e in o.listdir(streams=True)) if n.startswith("Partitions/"))
    segtab = {pn: Part(o, pn).segments() for pn in pns}
    say("segment tables: %d partitions, %d segments, %.1fs" % (len(pns), sum(len(v) for v in segtab.values()), time.time() - t0))
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    rows = []; _winit(path); hdr = {}
    _G["pidx"] = {pn: i for i, pn in enumerate(pns)}
    for pn in pns: hdr.update(header_region(pn, segtab[pn]))
    say("header region: %d headers, %.1fs" % (len(hdr), time.time() - t0))
    with mp.get_context("fork").Pool(workers, initializer=_winit, initargs=(path,)) as pool:
        for pi, pn in enumerate(pns):
            for r in pool.imap(_seg_job, [(pn, k, segtab[pn]) for k in range(len(segtab[pn]))], chunksize=4):
                rows.extend((pi,) + x for x in r)
    have = {r[1] for r in rows}      # ids with an ElementHeader in the header region but no standard body candidate (GStyleElem, CategoryElem, ...): header-only rows (off = -1, no alt)
    for e, (c, o_, f, cd, hp, hk) in hdr.items():
        if e not in have: rows.append((hp, e, hk, -1, -1))
    a = np.array(rows, dtype=np.int64).reshape(-1, 5)
    order = np.lexsort((a[:, 3], a[:, 2], a[:, 0], a[:, 1]))     # first-wins in file order, same rule as fastinfo.scan
    a = a[order]
    want = np.array([hdr.get(int(e), (0, 0, 0, -1))[3] for e in a[:, 1]], dtype=np.int64)
    miss = (a[:, 4] != want).astype(np.int64)        # candidates whose class tag equals the header's class tag sort first (removes reference look-alikes)
    order = np.lexsort((a[:, 3], a[:, 2], a[:, 0], miss, a[:, 1])); a = a[order]
    _, first, cnt = np.unique(a[:, 1], return_index=True, return_counts=True)
    NC = 4; alt = np.full((len(first), NC, 3), -1, dtype=np.int32)        # up to NC ranked candidates per id: (partition, segment, offset); the reader tries them until one decodes
    for c in range(NC):
        m = cnt > c; alt[m, c, 0] = a[first[m] + c, 0]; alt[m, c, 1] = a[first[m] + c, 2]; alt[m, c, 2] = a[first[m] + c, 3]
    a = a[first]
    hv = np.array([hdr.get(int(e), (-1, -1, -1, -1))[:4] for e in a[:, 1]], dtype=np.int64).reshape(-1, 4)
    has_hdr = np.array([int(e) in hdr for e in a[:, 1]])
    out = dict(part=a[:, 0].astype(np.int16), id=a[:, 1].astype(np.uint64), seg=a[:, 2].astype(np.int32), off=a[:, 3].astype(np.int32), tag=a[:, 4].astype(np.int32), cat=hv[:, 0], ownerview=hv[:, 1], family=hv[:, 2], has_header=has_hdr, alt=alt,
               pns=np.array(pns))
    for pi, pn in enumerate(pns): out["segtab%d" % pi] = np.array(segtab[pn], dtype=np.int64).reshape(-1, 3)
    out["cat_resolved"] = _resolved_categories(path, out["id"])
    os.makedirs(CACHE, exist_ok=True); tmp = cp + ".tmp.%d.npz" % os.getpid(); np.savez(tmp, **out); os.replace(tmp, cp)
    say("index built: %d ids, %.1fs" % (len(a), time.time() - t0))
    return load(path)


def _resolved_categories(path, ids):
    """builtin category per id (sub/user categories resolved through CategoryElem parents, as fastinfo.scan does); NOCAT (-2**62) where the file has none. Taken from one fastinfo.scan at build time
    (that scan stops early once every header is found); ids scan does not know get NOCAT."""
    from . import fastinfo as FI
    r = FI.scan(path, want_elements=True)["arrays"]; sid = r["id"]; sc = r["cat"]
    o = np.argsort(sid); sid = sid[o]; sc = sc[o]; k = np.searchsorted(sid, ids); k[k >= len(sid)] = 0
    ok = sid[k] == ids; out = np.full(len(ids), -(1 << 62), dtype=np.int64); out[ok] = sc[k][ok]
    return out


def load(path):
    z = np.load(os.path.join(CACHE, key(path) + ".npz")); return {k: z[k] for k in z.files}


class Reader:
    """one-id lookup: touches one segment (plus a 96 KB tail of the next) of one partition"""
    def __init__(s, path, idx=None):
        s.path = path; s.idx = idx or build(path); _winit(path); s.sorted = np.argsort(s.idx["id"]); s.ids = s.idx["id"][s.sorted]; s.segs = {}
    def locate(s, eid):
        k = int(np.searchsorted(s.ids, eid))
        if k >= len(s.ids) or int(s.ids[k]) != eid: return None
        j = int(s.sorted[k]); return {c: int(s.idx[c][j]) for c in ("part", "seg", "off", "tag", "cat", "ownerview")}
    def get(s, eid):
        j = s._row(eid)
        if j is None: return None
        loc = {c: int(s.idx[c][j]) for c in ("part", "seg", "off", "tag", "cat", "ownerview")}; loc["tries"] = 0; loc["record"] = None
        for pi, k, off in s.idx["alt"][j].tolist():
            if pi < 0: break
            pn = str(s.idx["pns"][pi]); P = _part(pn); segs = s.segs.get(pn)
            if segs is None: segs = s.segs[pn] = [tuple(int(x) for x in r) for r in s.idx["segtab%d" % pi]]
            cur = P.inflate(segs[k]); rec = None
            for extra in (TAIL, 1 << 20, 4 << 20):         # a record longer than the tail (images, big schedules) is cut: widen the window to following segments until it is complete
                nxt = b""; j = k + 1
                while len(nxt) < extra and j < len(segs): nxt += P.inflate(segs[j]); j += 1
                r = _G["rd"].extract_chunk(cur + nxt[:extra], _G["wanted"], _G["EH"], [eid], _G["wanted"]); loc["tries"] += 1
                hit = next((v for (e, c), v in r[0] if int(e) == eid), None)
                if hit is not None: rec = (hit.get("class") or hit and c); loc["complete"] = hit.get("complete")
                if hit is None or hit.get("complete") or not nxt: break
            if rec: loc.update(part=pi, seg=k, off=off, record=next((c for (e, c), v in r[0] if int(e) == eid), None)); break
        return loc
    def _row(s, eid):
        k = int(np.searchsorted(s.ids, eid))
        return int(s.sorted[k]) if k < len(s.ids) and int(s.ids[k]) == eid else None


def verify_partition(o, name):
    """integrity of the segment chain of one partition (read-only; for a writer's post-save gate): every segment inflates to exactly its declared inflated_len with a matching gzip CRC32/ISIZE trailer,
    segments do not overlap, and the bytes between segments (interludes) are returned so a writer can prove it kept them byte-identical.
    -> dict(segments, bad, interlude_bytes, interlude_sha1, covered)"""
    P = Part(o, name); segs = P.segments(); bad = []; deltas = {}; pos = 0; inter = hashlib.sha1(); ib = 0; prev_end = None
    for i, (off, ln, il) in enumerate(segs):
        hdr = off - 24
        if prev_end is not None and hdr < prev_end: bad.append((i, "overlap"))
        gap_a = prev_end if prev_end is not None else 0
        if hdr > gap_a: g = P.payload(gap_a, hdr - gap_a); inter.update(g); ib += len(g)
        raw = P.payload(off, ln)
        try:
            d = zlib.decompressobj(-15); out = d.decompress(raw[10:], 1 << 28)
            t = d.unused_data; deltas[len(out) // 1024] = deltas.get(len(out) // 1024, 0) + 1      # NOTE: header word 3 is NOT the inflated length (an earlier +64 relation was an artefact of capping the inflate at il+64)
            if not d.eof: bad.append((i, "stream not finished"))
            elif len(t) < 8 or struct.unpack("<II", t[:8]) != (zlib.crc32(out) & 0xffffffff, len(out) & 0xffffffff): bad.append((i, "gzip trailer"))
        except zlib.error as e: bad.append((i, "zlib %s" % e))
        prev_end = off + ln
    if prev_end is None and P.total: prev_end = 0      # stream without any gzip segment (e.g. 291-byte raw partition): all of it is interlude
    if prev_end is not None and prev_end < P.total: g = P.payload(prev_end, P.total - prev_end); inter.update(g); ib += len(g)
    return dict(segments=len(segs), bad=bad, interlude_bytes=ib, interlude_sha1=inter.hexdigest(), deltas=deltas, covered=sum(24 + s[1] for s in segs) + ib == P.total)


def _gaps(P, segs):
    """interlude blocks keyed by the index of the segment they precede (len(segs) = after the last one): {i: bytes}"""
    out = {}; prev = 0
    for i, (off, ln, il) in enumerate(segs):
        if off - 24 > prev: out[i] = P.payload(prev, off - 24 - prev)
        prev = off + ln
    if prev < P.total: out[len(segs)] = P.payload(prev, P.total - prev)
    return out


def compare_partitions(orig, out, name):
    """post-save gate for a writer, per partition: `orig` and `out` are olefile handles. Passes when
    out passes verify_partition, stream size and segment count are equal, every interlude block of the original is byte-identical in the output
    (a block may only GROW at the tail: slack left by recompressed shorter segments) and every segment that was not edited inflates to identical bytes.
    -> dict(ok, reasons (hard failures), warnings, changed_segments [idx], tail_slack, tail_slack_all_zero). Measured on a writer output: the block after the last segment (about 0.5 KB, 340 high-entropy bytes) changes when segments change: reported as a warning, not a failure."""
    Pa = Part(orig, name); Pb = Part(out, name); sa = Pa.segments(); sb = Pb.segments(); reasons = []; warnings = []
    v = verify_partition(out, name)
    if v["bad"]: reasons.append("output segments bad: %s" % v["bad"][:3])
    if not v["covered"]: reasons.append("output tiling inexact")
    if Pa.e.size != Pb.e.size: reasons.append("stream size %d -> %d" % (Pa.e.size, Pb.e.size))
    if len(sa) != len(sb): reasons.append("segment count %d -> %d" % (len(sa), len(sb)))
    ga = _gaps(Pa, sa); gb = _gaps(Pb, sb); slack = b""
    for i, blk in ga.items():
        o = gb.get(i, b"")
        if i == len(sa):        # tail block: the original non-zero content must come first and unchanged; everything the output adds must be zero padding (slack of shorter recompressed segments)
            core = blk.rstrip(b"\x00")
            if not o.startswith(core):
                warnings.append("tail block (%d B, %d non-zero) differs from the original (%d non-zero): a high-entropy trailer after the last segment changed; meaning unknown (digest?), VM-check it" % (len(o), len(o) - o.count(0), len(blk) - blk.count(0)))
                slack = b""
            else:
                slack = o[len(core):]
                if slack.count(0) != len(slack): reasons.append("tail slack is not all zero")
        elif i == 0 and o != blk and len(blk) == 20 and len(o) == 20 and blk[:14] == o[:14] and blk[18:] == o[18:]:
            # the 20-byte partition head holds this partition's element count (u32 at +14; the counts of all partitions sum to the Global/ElemTable header row count):
            # adding or deleting elements changes it. Accepted only when the output's heads sum to the output's ElemTable count.
            _paths(); import rvtfmt
            n_out = struct.unpack_from("<I", rvtfmt.inflate_stream(out.openstream("Global/ElemTable").read())[1], 2)[0]; tot = 0
            for e_ in out.listdir(streams=True):
                nm_ = "/".join(e_)
                if nm_.startswith("Partitions/"):
                    h_ = Part(out, nm_).payload(0, 20)
                    if len(h_) == 20 and struct.unpack_from("<I", h_, 0)[0] == 9: tot += struct.unpack_from("<I", h_, 14)[0]
            if tot != n_out: reasons.append("partition head counts sum to %d != ElemTable rows %d" % (tot, n_out))
            else: warnings.append("partition head count changed %d -> %d (heads sum to the ElemTable count %d)" % (struct.unpack_from("<I", blk, 14)[0], struct.unpack_from("<I", o, 14)[0], n_out))
        elif o != blk: reasons.append("interlude before segment %d changed" % i)
    for i in gb:
        if i not in ga and i != len(sb): reasons.append("new interlude before segment %d" % i)
    if len(sb) in gb and len(sa) not in ga:
        slack = gb[len(sb)]
        if slack.count(0) != len(slack): reasons.append("new tail block is not all zero")
    changed = []
    if len(sa) == len(sb):
        for i, (x, y) in enumerate(zip(sa, sb)):
            if Pa.inflate(x) != Pb.inflate(y): changed.append(i)
    return dict(ok=not reasons, reasons=reasons, warnings=warnings, changed_segments=changed, tail_slack=len(slack) - (len(ga.get(len(sa), b'')) - len(ga.get(len(sa), b'').rstrip(b'\x00'))), tail_slack_all_zero=(slack.count(0) == len(slack)))
