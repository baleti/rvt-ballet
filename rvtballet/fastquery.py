"""rvt-ballet targeted queries on big .rvt files: decode ONLY the classes a query needs, cold, no index.

Why it is fast (measured on a 984 MB project file, see docs/rvt-fast-query.md):
- one fork pool: schema, ElemTable ids and the Rust RecDecoder are built ONCE in the master and inherited by the workers (fastinfo starts a fresh
  interpreter per 96 MB job: ~3 s CPU each);
- tasks are runs of whole gzip segments taken from the segment-header walk (elemindex.Part.segments, no inflate), so the load is balanced and a
  task is small; each worker reads its stored bytes with os.pread over contiguous sector runs (own fd, no shared file offset after fork);
- the Rust decoder is asked for the query classes only and for no ElementHeader (ElementHeader trees are what made the generic scan slow);
  headers are decoded in a second pass restricted to the few ids that need one (only_ids).
Results equal fastinfo.scan for the same query (first-wins in stream order, same reductions): tests/test_fastquery.py.
"""
import os, sys, struct, zlib, time, collections

PAGE_STORED = 65249; PAGE_PAYLOAD = 64896
TASK_MB = float(os.environ.get('RVT_Q_TASK_MB', '8'))          # decoded MB per task (plus the overlap)
OVL = int(os.environ.get('RVT_Q_OVERLAP_KB', '1024')) << 10     # decoded bytes of the following segments appended to a task (a record straddling the task end is decoded whole)
_G = {}


def _paths():
    from . import fastinfo as FI
    FI._paths()


class Stream:
    """payload bytes of one partition stream; pread over contiguous sector runs of the CFB chain (fork safe: own fd per process)"""
    def __init__(s, o, name):
        e = o.direntries[o._find(name)]; s.size = e.size; s.ss = o.sectorsize
        s.small = o.openstream(name).read() if e.size < o.minisectorcutoff else None
        s.chain = []
        if s.small is None:
            fat = o.fat; c = e.isectStart; n = len(fat)
            while 0 <= c < n and len(s.chain) <= n: s.chain.append(c); c = fat[c]
    def stored(s, fd, a, b):
        if s.small is not None: return s.small[a:b]
        ss = s.ss; out = []; b = min(b, s.size); k = a // ss
        while a < b:
            k = a // ss; run = 1
            last = (b - 1) // ss
            while k + run <= last and s.chain[k + run] == s.chain[k] + run: run += 1
            off = a - k * ss; n = min(run * ss - off, b - a)
            out.append(os.pread(fd, n, (s.chain[k] + 1) * ss + off)); a += n
        return b''.join(out)
    @property
    def total(s):
        if s.small is not None: return len(s.small) - (len(s.small) // PAGE_STORED) * (PAGE_STORED - PAGE_PAYLOAD)
        n = -(-s.size // PAGE_STORED); last = s.size - (n - 1) * PAGE_STORED
        return (n - 1) * PAGE_PAYLOAD + min(last, PAGE_PAYLOAD)
    def segments(s, fd, every=None, cb=None):
        """== elemindex.Part.segments (same walk and resync rule) through pread; cb(segs so far) every `every` segments (the master plans tasks while it walks)"""
        T = s.total; GZ = b'\x1f\x8b\x08\x00'; segs = []; head = s.payload(fd, 0, 64); i = head.find(GZ)
        if i < 24: return []
        hdr = i - 24
        while hdr is not None and hdr + 24 <= T:
            b = s.payload(fd, hdr, hdr + 28)
            if len(b) == 28:
                w = struct.unpack('<6I', b[:24])
                if b[24:28] == GZ and 18 <= w[2] and hdr + 24 + w[2] <= T and w[0] < 16 and w[3] > 0:
                    segs.append((hdr + 24, w[2], w[3])); hdr += 24 + w[2]
                    if cb and len(segs) % every == 0: cb(segs)
                    continue
            hdr = s._resync(fd, hdr, T)
        return segs
    def _resync(s, fd, a, T):
        GZ = b'\x1f\x8b\x08\x00'; step = 1 << 14
        while a < T:
            buf = s.payload(fd, a, min(T, a + step + 28)); p = 0
            while True:
                i = buf.find(GZ, p)
                if i < 0 or i > step: break
                h = a + i - 24
                if h >= 0:
                    w = struct.unpack('<6I', s.payload(fd, h, h + 24))
                    if w[0] < 16 and 18 <= w[2] and h + 24 + w[2] <= T and w[3] > 0: return h
                p = i + 1
            a += step; step = min(step << 1, 1 << 22)
        return None
    def payload(s, fd, a, b):
        """payload bytes [a, b) (page trailers stripped)"""
        if b <= a: return b''
        pa = a // PAGE_PAYLOAD; pb = (b - 1) // PAGE_PAYLOAD
        raw = s.stored(fd, pa * PAGE_STORED, pb * PAGE_STORED + PAGE_PAYLOAD)
        buf = b''.join(raw[i * PAGE_STORED: i * PAGE_STORED + PAGE_PAYLOAD] for i in range(pb - pa + 1))
        o = a - pa * PAGE_PAYLOAD; return buf[o:o + b - a]


def _inflate(raw):
    d = zlib.decompressobj(-15); out = d.decompress(raw[10:])
    return out


_LD = []


def _libdeflate():
    """libdeflate through ctypes when the system has it (Debian/Ubuntu libdeflate0, macOS brew, a libdeflate.dll next to python): 1.9x zlib
    (measured 887 vs 468 MB/s on the segments of a 984 MB file, identical bytes). None -> zlib. RVT_Q_ZLIB=1 forces zlib."""
    if _LD: return _LD[0]
    lib = None
    if not os.environ.get('RVT_Q_ZLIB'):
        import ctypes, ctypes.util
        for n in ('libdeflate.so.0', 'libdeflate.so', ctypes.util.find_library('deflate') or '', 'libdeflate.dylib', 'libdeflate.dll', 'deflate.dll'):
            if not n: continue
            try: L = ctypes.CDLL(n)
            except OSError: continue
            L.libdeflate_alloc_decompressor.restype = ctypes.c_void_p
            L.libdeflate_deflate_decompress_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
            lib = (L, ctypes); break
    _LD.append(lib); return lib


def inflate_run(buf, a, segs, sizes_out=None):
    """inflated bytes of consecutive segments [(payload offset, stored_len, x)], `buf` = payload bytes from offset `a`. A segment's stored bytes are
    [10-byte gzip header][deflate][CRC32][ISIZE][8-byte footer]: libdeflate inflates straight into one buffer sized from the ISIZE fields (an ISIZE that does
    not match the inflated size falls back to zlib for that segment)"""
    lib = _libdeflate()
    if lib is None:
        parts = [_inflate(buf[off - a: off - a + ln]) for off, ln, _ in segs]
        if sizes_out is not None: sizes_out.extend(len(x) for x in parts)
        return b''.join(parts)
    L, C = lib; d = _G.get('ldd')
    if d is None or _G.get('ldd_pid') != os.getpid(): d = _G['ldd'] = L.libdeflate_alloc_decompressor(); _G['ldd_pid'] = os.getpid()
    sizes = [struct.unpack_from('<I', buf, off - a + ln - 12)[0] if ln >= 34 else 0 for off, ln, _ in segs]
    out = bytearray(sum(sizes)); ob = C.addressof((C.c_char * max(1, len(out))).from_buffer(out)) if out else 0
    ib = C.cast(C.c_char_p(buf), C.c_void_p).value; ai = C.c_size_t(); ao = C.c_size_t(); o = 0; fix = []
    for i, ((off, ln, _), sz) in enumerate(zip(segs, sizes)):
        r = L.libdeflate_deflate_decompress_ex(d, ib + off - a + 10, ln - 10, ob + o, sz, C.byref(ai), C.byref(ao)) if sz else 1
        if r != 0 or ao.value != sz: fix.append(i)
        o += sz
    if not fix:
        if sizes_out is not None: sizes_out.extend(sizes)
        return bytes(out)
    parts = []; o = 0                         # rare: rebuild with zlib for the odd segments
    for i, ((off, ln, _), sz) in enumerate(zip(segs, sizes)):
        parts.append(_inflate(buf[off - a: off - a + ln]) if i in fix else bytes(out[o:o + sz])); o += sz
    if sizes_out is not None: sizes_out.extend(len(x) for x in parts)
    return b''.join(parts)


def plan(pi, pn, segs):
    """decode tasks of one partition in stream order: (key, pn, segment list, number of main segments); the tail of the list is the overlap"""
    tasks = []; per = TASK_MB * 1e6; k = 0; n_ = 0
    while k < len(segs):
        j = k; n = 0
        while j < len(segs) and (n < per or j == k): n += segs[j][2]; j += 1
        m = j; ov = 0
        while m < len(segs) and ov < OVL: ov += segs[m][2]; m += 1
        tasks.append(((pi, k), pn, segs[k:m], j - k)); k = j
    return tasks


def _winit():
    _G['fd'] = os.open(_G['path'], os.O_RDONLY)
    try:      # task buffers are ~10 MB: above glibc's mmap threshold every one is a fresh mmap that is zeroed and page-faulted (sys time 2.8 -> 8 s); keep them on the heap
        import ctypes; libc = ctypes.CDLL('libc.so.6'); libc.mallopt(-3, 64 << 20); libc.mallopt(-1, 256 << 20)       # M_MMAP_THRESHOLD, M_TRIM_THRESHOLD
    except Exception: pass


def _job(job):
    """one pool job: ('walk', pi, pn) -> segment table; ('dec', key, pn, segs, nmain, wanted, note_eh, hdr_ids) -> records, headers, header candidates"""
    if job[0] == 'walk':
        return job, _G['streams'][job[2]].segments(_G['fd'])
    c0 = time.process_time(); w0 = time.time()
    _, key, pn, segs, nmain, wanted, note_eh, hdr_ids = job; S = _G['streams'][pn]; fd = _G['fd']
    a = segs[0][0]; b = segs[-1][0] + segs[-1][1]
    buf = S.payload(fd, a, b); sizes = []; chunk = inflate_run(buf, a, segs, sizes); del buf
    from . import fastinfo as FI
    rd = _G['rd']; recs = []; ehs = []; ehc = None
    specs = wanted if isinstance(wanted, list) and wanted and isinstance(wanted[0], dict) else ([{'tags': wanted}] if wanted else [])
    for sp in specs:              # {'tags', 'mode': 'fi' (fastinfo._reduce) | 'lite' (_lite), 'full': no-STOP decoder (type names), 'only': ids}
        d_ = _G['rd_full'] if sp.get('full') else rd
        r = d_.extract_chunk(chunk, sp['tags'], -1, sp.get('only'), [])
        lite = sp.get('mode') == 'lite'
        for (eid, c), rec in r[0]:
            if rec.get('fields'): recs.append(((int(eid), c), _lite(c, rec) if lite and c not in FI_REDUCED else FI._reduce(c, rec)))
    if note_eh: ehc = _eh_candidate_ids(chunk, sizes)
    if hdr_ids:
        r = rd.extract_chunk(chunk, [], _G['EH'], hdr_ids, [])
        for eid, h in r[1]:
            cd = h.get('m_classDef'); cd = cd.get('m_ref') if isinstance(cd, dict) else cd
            ehs.append((int(eid), (h.get('m_categroryId'), h.get('m_ownerViewId'), h.get('m_familyId'), cd)))
    return job[:2], (recs, ehs, ehc, (time.process_time() - c0, time.time() - w0, os.getpid()))


FI_REDUCED = ('CategoryElem', 'FamilySurrogate', 'FamSymSurrogate', 'GStyleElem')


def _plain(v, depth=0):
    """EID -> int, numbers/strings kept, short numeric vectors kept, pointers to an object with a name -> that name; everything else dropped (None)"""
    if type(v).__name__ == 'EID':                 # an int subclass: check it first (ids are unsigned on disk, -1 = none)
        x = int(v); return x - (1 << 64) if x >= 1 << 63 else x
    if v is None or isinstance(v, (bool, int, float, str)): return v
    if isinstance(v, (list, tuple)):
        if len(v) <= 16 and all(isinstance(x, (int, float)) or type(x).__name__ == 'EID' for x in v): return [_plain(x) for x in v]
        if depth == 0 and len(v) <= 64 and all(isinstance(x, (list, tuple)) and len(x) <= 4 for x in v): return [_plain(x, 1) for x in v]
        return None
    if isinstance(v, dict) and depth < 2:
        o = v.get('obj', v)
        if isinstance(o, dict) and isinstance(o.get('m_name'), str) and len(o) <= 3: return o['m_name']
    return None


def _lite(c, rec):
    """light record: top-level scalar / id / string / short-vector fields, plus 'name' when the record carries one (DatumPlane m_text, DBView m_viewName,
    SymbolInfo.m_name of a type, m_name)"""
    f = rec['fields']; out = {}
    for k, v in f.items():
        if k in ('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetAString', 'm_pParamValueSetElementId', 'm_geomSteps', 'm_pGeomTable', 'm_docAccess'): continue
        x = _plain(v)
        if x is not None: out[k] = x
    for k in ('m_text', 'm_viewName', 'm_symbolInfo', 'm_name'):
        if isinstance(out.get(k), str) and out[k]: out['name'] = out[k]; break
    return {'id': rec['id'], 'fields': out}


def _eh_candidate_ids(chunk, seg_sizes=None):
    """ids that have an ElementHeader CANDIDATE in this chunk (same test as the Rust candidate scan: a known id followed by the ElementHeader tag at +8+W or
    +4+W from the id; no decode): a superset of the headers the chunk holds, so a later header pass can skip every task without a candidate for the ids it wants"""
    import numpy as np
    W = _G['W']; t = _G['EH']; buf = np.frombuffer(chunk, np.uint8); n = len(buf)
    if n < 32 or t < 0: return np.zeros(0, np.uint64)
    q0 = np.flatnonzero(np.frombuffer(chunk, '<u2', count=n // 2) == t) * 2
    q1 = np.flatnonzero(np.frombuffer(chunk, '<u2', count=(n - 1) // 2, offset=1) == t) * 2 + 1
    q = np.concatenate([q0, q1])
    out = []
    for back in (8 + W, 4 + W):
        p = q - back; p = p[(p >= 0) & (p + W <= n)]
        if not len(p): continue
        v = np.zeros(len(p), np.uint64)
        for b in range(W): v |= buf[p + b].astype(np.uint64) << np.uint64(8 * b)
        ids = _G['ids']; k = np.searchsorted(ids, v); k[k >= len(ids)] = 0; ok = ids[k] == v; out.append((v[ok], p[ok]))
    if seg_sizes is None:
        return np.unique(np.concatenate([x[0] for x in out])) if out else np.zeros(0, np.uint64)
    # -> (ids, index of the segment holding the candidate) sorted by id
    if not out: return np.zeros(0, np.uint64), np.zeros(0, np.int32)
    v = np.concatenate([x[0] for x in out]); p = np.concatenate([x[1] for x in out])
    seg = (np.searchsorted(np.cumsum(seg_sizes), p, side='right')).astype(np.int32)
    o = np.lexsort((seg, v)); return v[o], seg[o]


def _ids_owned(et, W):
    """(sorted unique ElemTable ids as the decoder sees them, sorted ids that have an owner): same as elemindex._ids / fastinfo.scan, numpy only"""
    import numpy as np
    nh = struct.unpack_from('<I', et, 2)[0]
    def uniq(a):
        a = np.sort(a); return a[np.concatenate(([True], a[1:] != a[:-1]))] if len(a) else a
    if W == 4:
        n = min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28
        r = np.frombuffer(et, np.uint8, count=n * 28, offset=6).reshape(n, 28)
        a = r[:, :4].copy().view('<u4').ravel().astype(np.uint64); ow = r[:, 24:28].copy().view('<u4').ravel()
        return uniq(a), uniq(a[ow != 0xffffffff])
    n = (len(et) - 6) // 40
    if 0 < nh <= n: n = nh
    r = np.frombuffer(et, np.uint8, count=n * 40, offset=6).reshape(n, 40)
    a = r[:, :8].copy().view('<u8').ravel(); b = r[:, 20:28].copy().view('<u8').ravel(); ow = r[:, 28:36].copy().view('<u8').ravel()
    top = int(a.max()) + 16
    return uniq(np.concatenate([a, b[(b > 0) & (b < top)]])), uniq(a[ow != 0xffffffffffffffff])


def _setup(path, log):
    FI = __import__('rvtballet.fastinfo', fromlist=['x']); FI._tune(); FI._paths()
    import olefile, rvt_scan as S, rvt_decode as D, fmt_parser as fp, rvtfmt, rvt_fast as F
    from . import elemindex as EI
    t0 = time.time()
    o = olefile.OleFileIO(path); names = ['/'.join(e) for e in o.listdir(streams=True)]
    pns = sorted(n for n in names if n.startswith('Partitions/'))
    streams = {pn: Stream(o, pn) for pn in pns}; _G.pop('views', None)
    cls, _ = fp.parse(rvtfmt.inflate_stream(o.openstream('Formats/Latest').read())[1])
    W = S.id_size(cls); sch = D.Schema(cls)
    import numpy as np
    et = rvtfmt.inflate_stream(o.openstream('Global/ElemTable').read())[1]; ids, owned = _ids_owned(et, W); del et
    try: es = F.es_load(path)[0]
    except Exception: es = {}
    rd = F.make_recdecoder(sch, W, es); rd.set_ids(ids.tolist())
    # second decoder WITHOUT the geometry STOP list: the stop at GeomStepList/GeomTable also drops what follows it, e.g. SymbolInfo.m_name (type names): 0 of 199
    # type names on the 2024 HVAC sample with STOP, 199 of 199 without. Used only for type records (fields would be slower for instances).
    rd_full = F._rc().RecDecoder(sch.c, W, [], D.STRCAP, D.EID, D.Desync)
    if es: rd_full.set_es(es)
    rd_full.set_ids(ids.tolist())
    cnames = {i + 12: c['name'] for i, c in enumerate(cls)}
    log('schema + decoder: %.2fs' % (time.time() - t0))
    _G.update(path=path, o=o, pns=pns, streams=streams, cls=cls, W=W, sch=sch, rd=rd, rd_full=rd_full, ids=ids, owned=owned,
              cnames=cnames, EH=sch.by.get('ElementHeader', -999) + 12)
    return _G


def subclasses(cls, root):
    """names of `root` and every class deriving from it (schema parent = tag of the base class, tag = index + 12)"""
    names = [c['name'] for c in cls]; out = set(); memo = {}
    def isa(i, depth=0):
        if i in memo: return memo[i]
        if names[i] == root: memo[i] = True; return True
        p = cls[i].get('parent'); p = p & 0x7fff if isinstance(p, int) else None          # bit 15 is a flag on some parent tags (DBViewSchedule: 0x8000 | tag)
        r = p is not None and 12 <= p < 12 + len(cls) and p - 12 != i and depth < 64 and isa(p - 12, depth + 1)
        memo[i] = r; return r
    return {names[i] for i in range(len(cls)) if isa(i)}


class Engine:
    """one fork pool for the whole query: segment walks (biggest partition first), each partition's decode tasks submitted as soon as its walk is back,
    later passes reuse the same workers. Results are keyed (partition index, first segment) so first-wins follows stream order."""
    def __init__(s, workers, log):
        s.log = log; s.workers = workers; s.pool = None; s.stat = []
        if workers > 1:
            import multiprocessing as mp
            s.pool = mp.get_context('fork').Pool(workers, initializer=_winit)
        else: _winit()
    def close(s):
        if s.pool: s.pool.terminate()
    def walk_and_decode(s, wanted, note_eh):
        """-> (segtab {pn: segs}, tasks {key: task}, results {key: (recs, ehs, ehc)})"""
        t0 = time.time(); pns = _G['pns']; order = sorted(range(len(pns)), key=lambda i: -_G['streams'][pns[i]].size)
        segtab = {}; tasks = {}; res = {}
        if s.pool is None:
            for pi in order:
                pn = pns[pi]; segtab[pn] = _job(('walk', pi, pn))[1]
                for t in plan(pi, pn, segtab[pn]): tasks[t[0]] = t; res[t[0]] = _job(('dec',) + t + (wanted, note_eh, None))[1][:3]
            return segtab, tasks, res
        import queue
        q = queue.Queue(); pending = 0
        def put(r): q.put(r)
        def err(e): q.put(('error', e))
        for pi in order[1:]: s.pool.apply_async(_job, (('walk', pi, pns[pi]),), callback=put, error_callback=err); pending += 1
        # the biggest partition (75 percent of a big file) is walked HERE while the workers walk and decode the others; its tasks are submitted as soon as
        # the prefix fixes them (a task whose overlap is complete before the walk position is identical to the one plan() makes from the full table)
        pi0 = order[0]; pn0 = pns[pi0]; sent = set()
        def early(segs):
            nonlocal pending
            for t in plan(pi0, pn0, segs):
                if t[0] in sent: continue
                if t[0][1] + len(t[2]) >= len(segs): break            # its overlap may still grow: wait
                sent.add(t[0]); tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, None),), callback=put, error_callback=err); pending += 1
        fd = os.open(_G['path'], os.O_RDONLY)
        try: segtab[pn0] = _G['streams'][pn0].segments(fd, every=512, cb=early)
        finally: os.close(fd)
        for t in plan(pi0, pn0, segtab[pn0]):
            if t[0] in sent:
                assert tasks[t[0]] == t, 'early task differs from plan()'
                continue
            tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, None),), callback=put, error_callback=err); pending += 1
        if len(segtab) == len(pns): tw = time.time() - t0
        else: tw = None
        while pending:
            r = q.get(); pending -= 1
            if r[0] == 'error': raise r[1]
            head, body = r
            if head[0] == 'walk':
                pi, pn = head[1], head[2]; segtab[pn] = body
                for t in plan(pi, pn, body):
                    tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, None),), callback=put, error_callback=err); pending += 1
                if len(segtab) == len(pns): tw = time.time() - t0
            else:
                res[head[1]] = body[:3]; s.stat.append(body[3])
        s._report('records', len(tasks), t0, 'walks done at %.2fs, %d segments' % (tw or 0, sum(map(len, segtab.values()))))
        return segtab, tasks, res
    def run(s, jobs, what):
        """[(key, pn, segs, nmain, wanted, note_eh, hdr_ids)] -> {key: (recs, ehs, ehc)}"""
        t0 = time.time(); out = {}
        if s.pool is None: out = {j[0]: _job(('dec',) + tuple(j))[1][:3] for j in jobs}
        else:
            for head, body in s.pool.imap_unordered(_job, [('dec',) + tuple(j) for j in jobs], chunksize=1): out[head[1]] = body[:3]; s.stat.append(body[3])
        s._report(what, len(jobs), t0)
        return out
    def _report(s, what, n, t0, extra=''):
        st = s.stat; s.stat = []
        if st:
            busy = collections.Counter()
            for c, w, pid in st: busy[pid] += w
            s.log('  task cpu %.1fs, task wall %.1fs (max %.2fs), worker busy max %.2fs min %.2fs' % (sum(x[0] for x in st), sum(x[1] for x in st), max(x[1] for x in st), max(busy.values()), min(busy.values())))
        s.log('%s: %d tasks, %d workers, %.2fs%s' % (what, n, s.workers, time.time() - t0, (', ' + extra) if extra else ''))


def header_jobs(segtab, tasks, res, want_ids):
    """header jobs for `want_ids`: only segments that hold an ElementHeader candidate of a wanted id (noted in the record pass), each window from that
    segment through OVL decoded bytes (the same tail a task has), windows of one task merged; asked for just those ids"""
    import numpy as np
    nd = np.array(sorted(int(i) for i in want_ids), np.uint64); jobs = []
    for key in sorted(res):
        ehc = res[key][2]
        if ehc is None or not len(ehc[0]): continue
        sel = np.isin(ehc[0], nd)
        if not sel.any(): continue
        _, pn, tsegs, nmain = tasks[key]; pi, k0 = key; segs = segtab[pn]
        hit_ids = sorted(set(ehc[0][sel].tolist())); starts = sorted(set((k0 + ehc[1][sel]).tolist()))
        win = []
        for st in starts:
            st = max(0, st - 1)                # from the previous segment: a record's bytes before its id may sit there
            m = st; ov = 0
            while m < len(segs) and (m <= st + 1 or ov < OVL): ov += segs[m][2]; m += 1
            if win and st <= win[-1][1]: win[-1][1] = max(win[-1][1], m)
            else: win.append([st, m])
        for a, b in win: jobs.append(((pi, a), pn, segs[a:b], b - a, [], False, hit_ids))
    return jobs


def classes(path, want, header_ids=None, workers=None, log=None, last_wins=False):
    """generic primitive: first-wins reduced records of the classes `want` (names, or a predicate on the class name) and, optionally, the ElementHeaders
    (cat, owner view, family, classdef) of `header_ids` (callable: ids from the records). -> (records {(eid, class): rec}, headers {eid: tuple}, G)"""
    log = log or (lambda *a: None); workers = workers or _workers()
    G = _setup(path, log); pred = want if callable(want) else (lambda c, w=set(want): c in w)
    wanted = sorted(t for t, n in G['cnames'].items() if pred(n))
    E = Engine(workers, log)
    try:
        segtab, tasks, res = E.walk_and_decode(wanted, header_ids is not None)
        recs = {}
        for key in sorted(res):
            for k, v in res[key][0]:
                if last_wins or k not in recs: recs[k] = v          # last_wins: across tasks (inside one task the decoder keeps the first)
        hdr = {}
        hid = header_ids(recs) if callable(header_ids) else header_ids
        if hid:
            hres = E.run(header_jobs(segtab, tasks, res, hid), 'headers')
            for key in sorted(hres):
                for e, h in hres[key][1]:
                    if e not in hdr: hdr[e] = h
    finally: E.close()
    return recs, hdr, G


def _view_classes():
    if 'views' not in _G: _G['views'] = subclasses(_G['cls'], 'DBView')
    return _G['views']


def _workers():
    n = int(os.environ.get('RVT_Q_WORKERS', '0') or 0)
    if n: return n
    budget = float(os.environ.get('RVT_Q_MEM_GB', '3'))                 # per-worker peak measured ~150 MB (schema + decoder + one task)
    return max(1, min((os.cpu_count() or 2) - 1, int(budget * 1024 // 150)))


def sheets(path, workers=None, log=None, rule='reader'):
    """same list as fastinfo.scan(path)['sheets'] (number, name, issue date, drawn/approved by, revisions, views).
    rule='last' (EXPERIMENTAL, see demo-state NEEDS-FROM-RVTSHEETS 2026-11-14): last-wins on duplicate records and no ElemTable-owner skip; on a 984 MB project
    file it lists 413 sheets of which 412 equal Revit's 412 (the reader rule: 393 listed, 391 equal)"""
    log = log or (lambda *a: None); workers = workers or _workers(); t0 = time.time()
    # only real views (subclasses of DBView: sheets are DBViewDrafting), their Viewports and the revisions. fastinfo decodes every DBView* class: DBViewInfo,
    # DBViewType, the cutters are not views, and false DBViewInfo candidates (ids < 1000 inside bulk data) cost 128 of 170 CPU seconds on a 984 MB file
    # DBView* prefix as well: fastinfo names views of the DBView* classes only (TableView / PanelScheduleView on a sheet are not listed there either; kept equal)
    def want(c, keep=[]):
        return c.startswith('DBView') and c in _view_classes() or c in ('Viewport', 'ProjectRevision')
    def need_headers(full):
        # 2023+ files: a sheet lists no viewports; each Viewport is owned by its sheet (ElementHeader.m_ownerViewId)
        sheet_lists = [r['fields'].get('m_sheetViewportElemIds') for (e, c), r in full.items() if c == 'DBViewDrafting' and r['fields'].get('m_sheetNumber') and r['fields'].get('m_viewName') is not None]
        vps = [e for (e, c) in full if c == 'Viewport']
        return vps if vps and any(not x for x in sheet_lists) else []
    full, hdr, G = classes(path, want, need_headers, workers, log, last_wins=(rule == 'last'))
    import numpy as np
    owned = G['owned']; recs = {}; by = collections.defaultdict(list)
    def has_owner(e):
        k = int(np.searchsorted(owned, np.uint64(e))); return k < len(owned) and int(owned[k]) == e
    for (eid, c), r in full.items():
        if rule != 'last' and c in ('Level', 'Grid', 'RoomElem', 'DBViewDrafting') and has_owner(eid): continue
        by[c].append(r); recs.setdefault(eid, r)
    nm = lambda i: (recs[i]['fields'].get('m_text') or recs[i]['fields'].get('m_viewName') or recs[i]['fields'].get('m_name') or '') if i in recs else ''
    sh = []
    for r in by['DBViewDrafting']:
        f = r['fields']; n = f.get('m_viewName')
        if n is None or not f.get('m_sheetNumber'): continue
        sh.append({'id': r['id'], 'number': f.get('m_sheetNumber'), 'name': n, 'issue_date': f.get('m_issueDate'), 'drawn_by': f.get('m_drawnBy'), 'approved_by': f.get('m_approvedBy'),
                   'revision_ids': [int(v) for v in (f.get('m_explicitlyPresentRevisionIds') or []) if isinstance(v, (int,)) or hasattr(v, '__int__')],
                   'viewports': [int(v) for v in (f.get('m_sheetViewportElemIds') or [])]})
    vp = {r['id']: int(r['fields'].get('m_dbViewId', -1)) for r in by['Viewport']}
    on_sheet = collections.defaultdict(list)
    if hdr:
        from . import fastinfo as FI
        W = G['W']
        for v, dv in vp.items():
            h = hdr.get(v)
            if h is None or h[1] is None or not FI._plausible(h[1], W): continue
            ov = FI._sc(h[1], W)
            if ov not in (-1, 0): on_sheet[ov].append(dv)
    for s in sh:
        ids_ = [vp[v] for v in s.pop('viewports') if v in vp]
        s['views'] = [nm(d) for d in ids_ if d in recs] if ids_ else sorted(nm(d) for d in on_sheet.get(s['id'], []) if d in recs)
    sh.sort(key=lambda s: (str(s['number']), s['id']))
    revs = {r['id']: r['fields'] for r in by['ProjectRevision']}
    for s in sh: s['revisions'] = [{'number': revs[i].get('m_numberStr'), 'description': revs[i].get('m_description'), 'date': revs[i].get('m_date')} for i in sorted(s.get('revision_ids') or [], key=lambda i: revs.get(i, {}).get('m_sequenceNumber') or 0) if i in revs]
    log('sheets: %d, %.2fs' % (len(sh), time.time() - t0))
    return sh


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# collect: FilteredElementCollector-like primitive (OfClass / OfCategory + simple field filters), cold, no index

# Revit API class (or a common name) -> schema root classes; every subclass of a root is included. Any schema class name works too.
ALIASES = {
    'View': ('DBView',), 'ViewPlan': ('DBViewPlan',), 'ViewSection': ('DBViewSection',), 'View3D': ('DBView3d',), 'ViewDrafting': ('DBViewDrafting',),
    'ViewSheet': ('DBViewDrafting',), 'ViewSchedule': ('DBViewSchedule',), 'ViewFamilyType': ('DBViewType',),
    'Level': ('Level',), 'Grid': ('Grid',), 'Wall': ('ArcWall', 'SWall', 'FaceWall'), 'WallType': ('WallType',),
    'Floor': ('Floor',), 'FloorType': ('FloorAttributes',), 'Ceiling': ('Ceiling',), 'CeilingType': ('CeilingAttributes', 'CeilingType'),
    'RoofBase': ('RoofBase',), 'Roof': ('RoofBase',), 'RoofType': ('RoofAttributesBase',), 'Stairs': ('Stairs',), 'StairsType': ('StairsSym',),
    'Railing': ('BaseRailing', 'Railing'), 'RailingType': ('BaseRailingSym', 'BaseRailingAttr'), 'FamilyInstance': ('FamilyInstance',),
    'FamilySymbol': ('FamilySymbol',), 'ElementType': ('Symbol',), 'Family': ('Family',), 'Material': ('MaterialElem',), 'Room': ('RoomElem',),
    'TextNote': ('TextNote',), 'Dimension': ('Dimension',), 'IndependentTag': ('IndependentTag', 'TagElem'), 'RevitLinkInstance': ('LinkInstance',),
    'Revision': ('ProjectRevision',), 'Viewport': ('Viewport',), 'Phase': ('ProjectPhase',), 'Group': ('ElementGroup',), 'GroupType': ('ElementGroupType',),
    'CurtainGridLine': ('CurtainWallGridLine',), 'Mullion': ('Mullion',), 'Panel': ('Panel',),
}
# categories answered without a class: candidate classes (the ElementHeader category then filters exactly). Loadable-family categories -> FamilyInstance.
CATEGORY_CLASSES = {
    'Walls': ('ArcWall', 'SWall', 'FaceWall'), 'Floors': ('Floor',), 'Ceilings': ('Ceiling',), 'Roofs': ('RoofBase',), 'Stairs': ('Stairs', 'MultistoryStairs'),
    'Railings': ('BaseRailing', 'Railing'), 'Rooms': ('RoomElem',), 'Levels': ('Level',), 'Grids': ('Grid',), 'Views': ('DBView',), 'Sheets': ('DBViewDrafting',),
    'Text Notes': ('TextNote',), 'Dimensions': ('Dimension',), 'Materials': ('MaterialElem',), 'Curtain Wall Mullions': ('Mullion', 'FamilyInstance'),
    'Curtain Panels': ('Panel', 'FamilyInstance', 'ArcWall'), 'RVT Links': ('LinkInstance',),
}
LOADABLE = ('Doors', 'Windows', 'Furniture', 'Furniture Systems', 'Generic Models', 'Casework', 'Plumbing Fixtures', 'Lighting Fixtures', 'Electrical Fixtures',
            'Electrical Equipment', 'Mechanical Equipment', 'Specialty Equipment', 'Structural Columns', 'Columns', 'Structural Framing', 'Structural Foundations',
            'Planting', 'Entourage', 'Site', 'Parking', 'Lighting Devices', 'Communication Devices', 'Data Devices', 'Fire Alarm Devices', 'Security Devices',
            'Sprinklers', 'Air Terminals', 'Duct Fittings', 'Pipe Fittings', 'Pipe Accessories', 'Duct Accessories', 'Food Service Equipment', 'Medical Equipment',
            'Signage', 'Mass', 'Detail Items', 'Generic Annotations', 'Title Blocks')
TYPE_FIELDS = ('m_masterSymbolId', 'm_WallAttributesId', 'm_floorAttributesId', 'm_ceilingAttributesId', 'm_roofAttributesId', 'm_attrId', 'm_symbolId', 'm_typeId', 'm_dbViewTypeId')


def _class_set(cls, names):
    allc = {c['name'] for c in cls}; out = set()
    for n in ([names] if isinstance(names, str) else names):
        roots = ALIASES.get(n, (n,))
        for r in roots:
            if r in allc: out |= subclasses(cls, r)
    return out


def _cat_table():
    import json
    if 'catnames' not in _G:
        _G['catnames'] = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'category_names.json'))).items()}
    return _G['catnames']


def _cat_id(category):
    if isinstance(category, int) or (isinstance(category, str) and category.lstrip('-').isdigit()): return int(category)
    t = _cat_table(); hits = [k for k, v in t.items() if v.lower() == str(category).lower()]
    if not hits: raise ValueError('unknown category %r' % category)
    return hits[0]


def _sid(v, W=8):
    if v is None: return None
    try: v = int(v)
    except Exception: return None
    b = 8 * W
    if v >= 1 << (b - 1): v -= 1 << b
    return v if -(1 << 31) <= v < (1 << 31) else None


def collect(path, cls=None, category=None, fields=None, where=None, workers=None, log=None, rule='last', names=True):
    """rows of every element of class `cls` (Revit API or schema class name / list; subclasses included) and/or `category` (built-in name or id), like
    FilteredElementCollector(doc).OfClass(..).OfCategory(..). Each row: id, class, name, type_id, type_name, level_id, level, category_id, category,
    owner_view_id, plus the raw fields in `fields` (light values: ids, numbers, strings, short vectors). where: {field: value} equality filters on row keys.
    rule: 'last' (default) = last record in stream order wins for an id with several records (sheets: 412/412 vs 391), 'first' = fastinfo's first-wins."""
    log = log or (lambda *a: None); workers = workers or _workers(); t0 = time.time()
    G = _setup(path, log); W = G['W']
    want = set()
    if cls: want = _class_set(G['cls'], cls)
    cat = _cat_id(category) if category is not None else None
    if cat is not None and not cls:
        nm = _cat_table().get(cat, '')
        roots = CATEGORY_CLASSES.get(nm) or (('FamilyInstance',) if nm in LOADABLE else None)
        if roots is None: raise ValueError('category %r needs --class (no class map for it yet)' % category)
        want = _class_set(G['cls'], roots)
    if not want: raise ValueError('no schema class matches %r' % (cls,))
    tag_of = {n: t for t, n in G['cnames'].items()}
    aux = {'Level', 'CategoryElem', 'FamilySurrogate', 'FamSymSurrogate'}
    sym = subclasses(G['cls'], 'Symbol')
    spec = [{'tags': sorted(tag_of[n] for n in (want | aux) - sym if n in tag_of), 'mode': 'lite'}]
    spec = [x for x in spec if x['tags']]
    if want & sym: spec.append({'tags': sorted(tag_of[n] for n in want & sym if n in tag_of), 'mode': 'lite', 'full': True})      # type names need the no-STOP decoder
    E = Engine(workers, log)
    try:
        segtab, tasks, res = E.walk_and_decode(spec, True)
        full = {}
        for key in sorted(res):
            for k, v in res[key][0]:
                if rule == 'last' or k not in full: full[k] = v
        rows = {}
        for (eid, c), r in full.items():
            if c in want: rows[eid] = (c, r)
        # ElementHeaders of the result ids: category, owner view, family
        hdr = {}
        if rows:
            for key, (_, ehs, _) in sorted(E.run(header_jobs(segtab, tasks, res, list(rows)), 'headers').items()):
                for e, h in ehs:
                    if e not in hdr: hdr[e] = h
        # type records (names) by id: only type classes, no-STOP decoder, only the referenced ids
        tid = {}
        for e, (c, r) in rows.items():
            f = r['fields']
            for k in TYPE_FIELDS:
                v = f.get(k)
                if isinstance(v, int) and v > 0: tid[e] = v; break
        types = {}
        need = sorted({v for v in tid.values()} - {e for (e, c) in full})
        if names and need:
            stags = sorted(tag_of[n] for n in sym if n in tag_of)
            jobs = [t + ([{'tags': stags, 'mode': 'lite', 'full': True, 'only': need}], False, None) for t in (tasks[k] for k in sorted(tasks))]
            for key, (rr, _, _) in sorted(E.run(jobs, 'types by id').items()):
                for (e, c), r in rr:
                    if rule == 'last' or e not in types: types[e] = (c, r)
        tv = set(tid.values())
        for (e, c), r in full.items():
            if e in tv and e not in types: types[e] = (c, r)
    finally: E.close()
    # categories: header id, sub/user categories through CategoryElem parents (as fastinfo / categories.resolve)
    from . import categories as CT
    parent = {}
    for (e, c), r in full.items():
        if c == 'CategoryElem' and r['fields'].get('m_parentCategoryId') is not None: parent[e] = _sid(r['fields']['m_parentCategoryId'], W)
    def builtin(v):
        for _ in range(4):
            if v is None: return None
            if v < -1: return v
            if v > 0 and v in parent: v = parent[v]
            else: return None
        return None
    levels = {e: r['fields'].get('m_text') for (e, c), r in full.items() if c == 'Level'}
    ct = _cat_table(); out = []
    for e, (c, r) in sorted(rows.items()):
        f = r['fields']; h = hdr.get(e)
        craw = _sid(h[0], W) if h else None; cb = builtin(craw)
        if cat is not None and cb != cat and craw != cat: continue
        t = tid.get(e); tr = types.get(t)
        lv = f.get('m_assocLevelId'); lv = lv if isinstance(lv, int) and lv > 0 else None
        row = {'id': e, 'class': c, 'name': f.get('name'), 'type_id': t, 'type_name': tr[1]['fields'].get('name') if tr else None,
               'level_id': lv, 'level': levels.get(lv), 'category_id': cb if cb is not None else craw, 'category': ct.get(cb) if cb is not None else None,
               'owner_view_id': _sid(h[1], W) if h else None}
        if row['owner_view_id'] in (-1, 0): row['owner_view_id'] = None
        if row['name'] is None and row['type_name']: row['name'] = row['type_name']           # Revit: Element.Name of an instance is its type name
        for k in (fields or ()):
            if k not in row: row[k] = f.get(k)
        if where and any(str(row.get(k)) != str(v) for k, v in where.items()): continue
        out.append(row)
    log('collect: %d rows, %.2fs' % (len(out), time.time() - t0))
    return out


READY = {'views': {'cls': 'View'}, 'levels': {'cls': 'Level'}, 'grids': {'cls': 'Grid'}, 'walls': {'cls': 'Wall'}, 'wall-types': {'cls': 'WallType'},
         'floors': {'cls': 'Floor'}, 'floor-types': {'cls': 'FloorType'}, 'roofs': {'cls': 'RoofBase'}, 'ceilings': {'cls': 'Ceiling'}, 'stairs': {'cls': 'Stairs'},
         'railings': {'cls': 'Railing'}, 'rooms': {'cls': 'Room'}, 'doors': {'category': 'Doors'}, 'windows': {'category': 'Windows'},
         'furniture': {'category': 'Furniture'}, 'generic-models': {'category': 'Generic Models'}, 'columns': {'category': 'Structural Columns'},
         'framing': {'category': 'Structural Framing'}, 'family-instances': {'cls': 'FamilyInstance'}, 'types': {'cls': 'FamilySymbol'}, 'families': {'cls': 'Family'},
         'materials': {'cls': 'Material'}, 'revisions': {'cls': 'Revision'}, 'schedules': {'cls': 'ViewSchedule'}, 'links': {'cls': 'RevitLinkInstance'},
         'text-notes': {'cls': 'TextNote'}, 'dimensions': {'cls': 'Dimension'}, 'curtain-panels': {'category': 'Curtain Panels'}}


def main(argv):
    import argparse, json
    ap = argparse.ArgumentParser(prog='rvt-ballet query', description='cold targeted queries on a .rvt (no index): sheets, collect, or a ready command: ' + ', '.join(sorted(READY)))
    ap.add_argument('cmd', choices=('sheets', 'collect') + tuple(sorted(READY))); ap.add_argument('file')
    ap.add_argument('--class', dest='cls', help='collect: Revit API or schema class name(s), comma separated (subclasses included)')
    ap.add_argument('--category', help='collect: built-in category name or id'); ap.add_argument('--fields', default='', help='extra raw fields, comma separated')
    ap.add_argument('--where', action='append', default=[], help='KEY=VALUE equality filter on a row key (repeatable)')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--tsv', action='store_true'); ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--workers', type=int, default=0); ap.add_argument('--rule', choices=('reader', 'last', 'first'), default=None, help='sheets: reader (default, = rvt-ballet sheets) or last; collect: last (default) or first')
    a = ap.parse_args(argv)
    log = (lambda m: print(m, file=sys.stderr)) if a.verbose else None
    if a.cmd == 'sheets':
        sh = sheets(a.file, workers=a.workers or None, log=log, rule=a.rule or 'reader')
        if a.json: print(json.dumps(sh, indent=1, default=str)); return 0
        print('Sheets (%d):' % len(sh))
        for s in sh: print('  %-8s %s%s%s | views: %s' % (s['number'], s['name'], ('  (issued %s)' % s['issue_date']) if s.get('issue_date') else '', ('  rev %s' % '; '.join('%s %s' % (x['number'], x['description']) for x in s['revisions'])) if s.get('revisions') else '', ', '.join(s['views']) or '-'))
        return 0
    q = dict(READY.get(a.cmd, {}))
    if a.cls: q['cls'] = a.cls.split(',')
    if a.category: q['category'] = a.category
    flds = [x for x in a.fields.split(',') if x]
    where = dict(w.split('=', 1) for w in a.where)
    rows = collect(a.file, q.get('cls'), q.get('category'), flds, where or None, workers=a.workers or None, log=log, rule=a.rule or 'last')
    cols = ['id', 'class', 'name', 'type_name', 'level', 'category'] + [k for k in flds if k not in ('id', 'class', 'name')]
    if a.json: print(json.dumps(rows, indent=1, default=str)); return 0
    if a.tsv:
        print('\t'.join(cols))
        for r in rows: print('\t'.join('' if r.get(k) is None else str(r.get(k)) for k in cols))
        return 0
    print('%s (%d):' % (a.cmd, len(rows)))
    for r in rows: print('  ' + ' | '.join('' if r.get(k) is None else str(r.get(k)) for k in cols))
    return 0


if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
