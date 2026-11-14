"""rvt-ballet admin-data reader: info / sheets / views / levels / grids / counts / elements of a .rvt WITHOUT conversion and with bounded memory.

Never imports the geometry pipeline. Partition streams are read from the CFB sector chain in blocks (never a whole stream), gzip members are inflated
one after the other, joined into windows of ~WINDOW decoded bytes (overlap OVERLAP, so a record straddling a window edge is decoded whole in the next
window) and handed to the Rust RecDecoder.extract_chunk (rvt_fast), slim (empty fields) for every class except the few admin classes
(Level, Grid, DBView*, Viewport, ProjectPhase, ProjectInfo). Per-element data is reduced to small tuples at once, so peak RSS depends on WINDOW, not on file size.
"""
import os, sys, re, struct, zlib, io, zipfile, collections, json, time

PAGE_STORED = 65249; PAGE_PAYLOAD = 64896; GZ = b'\x1f\x8b\x08\x00'
WINDOW = int(os.environ.get('RVT_INFO_WINDOW_MB', '3')) << 20
OVERLAP = int(os.environ.get("RVT_INFO_OVERLAP_KB", "1024")) << 10
FULL_CLASSES = ('FamilySurrogate', 'FamSymSurrogate', 'GStyleElem', 'CategoryElem', 'Level', 'Grid', 'ProjectPhase', 'ProjectInfo', 'Viewport', 'ProjectRevision')
FULL_PREFIX = ('DBView',)
MAX_MEMBER = 1 << 30
STATS = {'crc_bad': 0, 'members': 0}      # damaged-block counters (reset by scan); a bad gzip CRC/size trailer on a member that inflated to its end = real damage


def _tune():
    """memory hygiene for the Rust decoder: one decode thread (RVT_THREADS) and one malloc arena; measured on a 15 MB file whose 17k ElementHeaders hold 60 KB trees each: peak 1.9 GB -> 0.43 GB"""
    os.environ.setdefault('RVT_THREADS', '1')
    try:
        import ctypes; ctypes.CDLL('libc.so.6').mallopt(-8, 1)       # M_ARENA_MAX
    except Exception: pass


def _rss_mb():
    try:
        return int(open('/proc/self/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE') >> 20
    except Exception: return -1


def _trim():
    try:
        import ctypes; ctypes.CDLL('libc.so.6').malloc_trim(0)
    except Exception: pass


def _paths():
    for p in (os.environ.get('RVT_READER_DIR'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/src/rvt-core/python')):
        if p and os.path.isdir(p) and p not in sys.path: sys.path.append(p)
    try:
        from . import plat   # noqa: F401  (adds the sibling rvt-core / rvt-sheets dirs to sys.path)
    except Exception: pass


def _strip(buf, pages):
    out = bytearray()
    for p in range(pages): out += buf[p * PAGE_STORED: p * PAGE_STORED + PAGE_PAYLOAD]
    return bytes(out)


def chain_blocks(o, name, block_pages=256, lo_page=0, hi_page=None):
    """payload of stream `name` (353-byte page trailers stripped) in blocks of ~block_pages pages, read from the CFB sector chain
    (olefile.openstream would load the whole stream: 770 MB for one partition of a big central file). lo_page/hi_page select a page range (a segment for a worker process)."""
    e = o.direntries[o._find(name)]; ss = o.sectorsize; fat = o.fat; fp = o.fp
    if e.size < o.minisectorcutoff:                      # tiny streams live in the mini stream (not the sector chain): olefile reads those (< 4 KB)
        if lo_page: return
        raw = o.openstream(name).read(); pages = len(raw) // PAGE_STORED
        yield _strip(raw, pages) + raw[pages * PAGE_STORED:]; return
    lo_b = lo_page * PAGE_STORED; hi_b = e.size if hi_page is None else min(e.size, hi_page * PAGE_STORED)
    if lo_b >= hi_b: return
    first = lo_b // ss; last = (hi_b - 1) // ss; nsect = len(fat); sect = e.isectStart; secs = []
    for idx in range(last + 1):
        if not (0 <= sect < 0xFFFFFFFA): break
        if idx >= first: secs.append(sect)
        sect = fat[sect] if sect < nsect else -1
    want = block_pages * PAGE_STORED; buf = bytearray(); pos = first * ss; k = 0
    while k < len(secs):
        run = 1
        while k + run < len(secs) and run < 4096 and secs[k + run] == secs[k] + run: run += 1
        fp.seek((secs[k] + 1) * ss); chunk = fp.read(run * ss); k += run
        if not chunk: break
        a0 = max(lo_b - pos, 0); a1 = min(len(chunk), hi_b - pos); pos += run * ss
        if a1 > a0: buf += chunk[a0:a1]
        if len(buf) >= want:
            pages = len(buf) // PAGE_STORED
            blk = _strip(buf, pages); del buf[:pages * PAGE_STORED]
            yield blk
    if buf:
        pages = len(buf) // PAGE_STORED
        yield _strip(buf, pages) + bytes(buf[pages * PAGE_STORED:])


def members(blocks):
    """decoded gzip members of a payload-block iterator, one at a time. Offset based (no per-member copies of the rest of the block) and the deflate input is fed
    in 64 KB slices, so unused_data never drags the remaining megabytes along (that was quadratic: 10 MB/s). A stray marker inside bulk data is skipped like rvt2text.segments."""
    buf = bytearray(); it = iter(blocks); eof = [False]; pos = 0
    def more():
        nonlocal pos
        if eof[0]: return False
        try: blk = next(it)
        except StopIteration: eof[0] = True; return False
        buf.extend(blk); return True
    while True:
        if pos > (1 << 20): del buf[:pos]; pos = 0               # compact only here: i / q below are buffer indices
        i = buf.find(GZ, pos)
        while i < 0:
            pos = max(pos, len(buf) - 3)
            if not more(): return
            i = buf.find(GZ, pos)
        pos = i + 10
        while len(buf) < pos and more(): pass
        d = zlib.decompressobj(-15); outs = []; total = 0; ok = False; bad = False; q = pos
        while True:
            if q >= len(buf):
                if not more(): break
                continue
            piece = bytes(buf[q:q + 65536])
            try: out = d.decompress(piece, MAX_MEMBER - total)
            except zlib.error: bad = True; break
            if out: outs.append(out); total += len(out)
            if d.unconsumed_tail: raise ValueError('corrupt block: member expands beyond %d bytes' % MAX_MEMBER)
            if d.eof: q += len(piece) - len(d.unused_data); ok = True; break
            q += len(piece)
        if bad: pos = i + 4; continue                             # false marker: resume right after it
        if not ok: return                                          # stream ends inside a member
        pos = q
        data = b''.join(outs)
        while len(buf) < pos + 8 and more(): pass
        STATS['members'] += 1
        if len(buf) >= pos + 8:
            crc, isz = struct.unpack_from('<II', buf, pos)
            if crc != (zlib.crc32(data) & 0xffffffff) or isz != (len(data) & 0xffffffff): STATS['crc_bad'] += 1
        yield data
        pos += 8                                                   # gzip CRC32/ISIZE trailer


def windows(blocks):
    """(chunk, final): joined member data. Every chunk but the last stops OVERLAP before the window end; the next window starts 2*OVERLAP before it."""
    carry = b''; parts = []; n = 0
    for m in members(blocks):
        parts.append(m); n += len(m)
        if n >= WINDOW:
            w = carry + b''.join(parts); parts = []; n = 0
            yield w[:len(w) - OVERLAP], False
            carry = w[len(w) - 2 * OVERLAP:]; w = None
    yield carry + b''.join(parts), True


def basic_info(o):
    b = o.openstream('BasicFileInfo').read(); i = b.find('Worksharing'.encode('utf-16le'))
    t = b[i:].decode('utf-16le', 'ignore') if i >= 0 else b.decode('utf-16le', 'ignore')
    d = collections.OrderedDict()
    for l in re.split(r'[\r\n]+', t):
        if ':' in l:
            k, v = l.split(':', 1); d[k.strip()] = v.strip()
    return d


def project_information(o, names):
    if 'ProjectInformation' not in names: return {}
    try:
        z = zipfile.ZipFile(io.BytesIO(o.openstream('ProjectInformation').read()))
        x = z.read(z.namelist()[0]).decode('utf-8', 'replace')
    except Exception: return {}
    out = {}
    for tag in ('title', 'BuildingName', 'OrganizationName', 'OrganizationDescription', 'Author', 'ProjectNumber', 'ProjectName', 'ProjectIssueDate', 'ProjectStatus', 'ClientName', 'Address'):
        m = re.search(r'<%s>([^<]*)</%s>' % (tag, tag), x, re.I)
        if m and m.group(1).strip(): out[tag] = m.group(1).strip()
    return out


def saves(o):
    """[(user, unix time)] from Global/DocumentIncrementTable: each save record is the user name (UTF-16) followed by 4 zero bytes, two ids, a zero u32 and the save time as unix seconds
    (verified against file mtimes of 4 seed files; implausible values are dropped)"""
    import rvtfmt
    PR = re.compile(rb'(?:[\x20-\x7e]\x00){3,}'); out = []
    try:
        pre, d, _ = rvtfmt.inflate_stream(o.openstream('Global/DocumentIncrementTable').read())
        for m in PR.finditer(d):
            if m.end() + 20 > len(d): continue
            ts = struct.unpack_from('<I', d, m.end() + 16)[0]
            if 1.0e9 < ts < 2.2e9: out.append((m.group().decode('utf-16le'), ts))
    except Exception: pass
    return out


def editors(o):
    import rvtfmt
    PR = re.compile(rb'(?:[\x20-\x7e]\x00){3,}')
    try:
        pre, dit, _ = rvtfmt.inflate_stream(o.openstream('Global/DocumentIncrementTable').read())
        c = collections.Counter(m.group().decode('utf-16le') for m in PR.finditer(dit))
        return [u for u, n in c.most_common() if re.search(r'[A-Za-z]{3}', u)][:30]
    except Exception: return []


_KEEP = {'ProjectRevision': ('m_description', 'm_date', 'm_numberStr', 'm_sequenceNumber', 'm_issuedBy', 'm_issuedTo', 'm_issued'), 'Level': ('m_text',), 'Grid': ('m_text',), 'ProjectPhase': ('m_name',), 'ProjectInfo': ('m_text', 'm_name'), 'Viewport': ('m_dbViewId',), 'FamilySurrogate': ('m_categoryId', 'm_elemId'), 'FamSymSurrogate': ('m_categoryId', 'm_elemId'), 'GStyleElem': ('m_categoryId',), 'CategoryElem': ('m_ownerId',)}
_KEEP_VIEW = ('m_viewName', 'm_sheetNumber', 'm_issueDate', 'm_drawnBy', 'm_sheetViewportElemIds', 'm_isTemplate', 'm_scale', 'm_text', 'm_name', 'm_approvedBy', 'm_explicitlyPresentRevisionIds', 'm_revNumMap')


def _reduce(c, rec):
    """keep only the fields the lists need: DBView/ViewSchedule records are large trees (the retained full records were ~250 MB of the baseline RSS on a 900 MB file)"""
    f = rec['fields']; keep = _KEEP_VIEW if c.startswith('DBView') else _KEEP.get(c, ())
    out = {k: f[k] for k in keep if k in f}
    if c == 'CategoryElem':
        pc = f.get('m_pCategory'); pc = pc.get('obj', pc) if isinstance(pc, dict) else pc
        if isinstance(pc, dict): out['m_parentCategoryId'] = pc.get('m_parentCategoryId'); out['m_name'] = pc.get('m_name')
    if c == 'Level':
        ps = f.get('m_pSurface'); ps = ps.get('obj', ps) if isinstance(ps, dict) else ps
        if isinstance(ps, dict) and 'm_origin' in ps: out['m_pSurface'] = {'m_origin': list(ps['m_origin'])}
    return {'id': rec['id'], 'fields': out}


def _plausible(v, W):
    v = _sc(v, W); return -(1 << 31) <= v < (1 << 31)


def _sc(v, W):
    v = int(v); return v - (1 << (8 * W)) if v >= 1 << (8 * W - 1) else v


def file_info(path):
    """seconds: BasicFileInfo, project information, editors. No partition is touched."""
    _paths()
    import olefile
    o = olefile.OleFileIO(path); names = ['/'.join(e) for e in o.listdir(streams=True)]
    r = {'file_size': os.path.getsize(path), 'info': dict(basic_info(o)), 'project': project_information(o, names), 'editors': editors(o),
         'partitions': sum(1 for n in names if n.startswith('Partitions/'))}
    sv = saves(o)
    if sv:
        u, t = max(sv, key=lambda x: x[1]); r['last_saved_by'] = u; r['last_saved'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t)) + ' UTC'
        r['first_saved'] = time.strftime('%Y-%m-%d', time.gmtime(min(x[1] for x in sv))); r['save_records'] = len(sv)
    r['mtime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(path)))
    return r


GROUP = int(os.environ.get('RVT_INFO_GROUP', '0'))     # 0 = off (id groups did not lower the peak; kept for experiments)


def _extract_groups(rd, chunk, wanted, EH, slim_tags, idlist):
    """rd.extract_chunk over id groups: a decoded ElementHeader carries a m_regenHistory/m_parents tree (60 KB of Python objects for some elements), so one call over a
    header-dense window returned 1.5-1.9 GB of Python objects (15 MB file). Groups of GROUP ids bound that per call; results are reduced before the next call."""
    if not GROUP or len(idlist) <= GROUP: return rd.extract_chunk(chunk, wanted, EH, None, slim_tags)
    recs = []; ehs = []
    for a in range(0, len(idlist), GROUP):
        r = rd.extract_chunk(chunk, wanted, EH, idlist[a:a + GROUP], slim_tags)
        recs.extend(r[0]); ehs.extend(_reduce_headers(r[1]))
    return recs, ehs


def _reduce_headers(ehs):
    out = []
    for eid, h in ehs: out.append((eid, {k: h.get(k) for k in ('m_categroryId', 'm_ownerViewId', 'm_familyId', 'm_pBBox')}))
    return out


SEG_MB = float(os.environ.get('RVT_INFO_SEG_MB', '96'))        # stored MB of a partition handled per worker process (a fresh process: allocator state/baseline RSS reset)
SEG_EXTRA_PAGES = 64


def scan(path, log=None, want_elements=False, progress=None, _seg=None, _out=None):
    """-> dict: levels, grids, views, sheets, phases, counts (by category), class_counts, view_owned, stats, elements (when want_elements)"""
    _tune(); _paths()
    import olefile, rvt_scan as S, rvt_decode as D, rvt_inventory as I, fmt_parser as fp, rvtfmt, rvt_fast as F, rvt_entities as E
    t0 = time.time(); say = log or (lambda *a: None); STATS['crc_bad'] = 0; STATS['members'] = 0
    o = olefile.OleFileIO(path); names = ['/'.join(e) for e in o.listdir(streams=True)]
    cls, _ = fp.parse(rvtfmt.inflate_stream(o.openstream('Formats/Latest').read())[1])
    W = S.id_size(cls); sch = D.Schema(cls)
    et = rvtfmt.inflate_stream(o.openstream('Global/ElemTable').read())[1]
    nh = struct.unpack_from('<I', et, 2)[0]
    if W == 4: ids = {struct.unpack_from('<I', et, 6 + 28 * k)[0] for k in range(min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28)}; prim_ids = set(ids)
    else:
        n = (len(et) - 6) // 40
        if 0 < nh <= n: n = nh
        ids = {struct.unpack_from('<Q', et, 6 + 40 * k)[0] for k in range(n)}; prim_ids = set(ids)
        top = max(ids) + 16
        ids |= {v for v in (struct.unpack_from('<Q', et, 6 + 40 * k + 20)[0] for k in range(n)) if 0 < v < top}
    owner = {}
    if W == 4:
        for k in range(min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28):
            r = struct.unpack_from('<7I', et, 6 + 28 * k)
            if r[6] != 0xffffffff: owner[r[0]] = r[6]
    else:
        for k in range(min(nh, (len(et) - 6) // 40) if nh else (len(et) - 6) // 40):
            ow = struct.unpack_from('<Q', et, 6 + 40 * k + 28)[0]
            if ow != 0xffffffffffffffff: owner[struct.unpack_from('<Q', et, 6 + 40 * k)[0]] = ow
    del et
    EH = sch.by.get('ElementHeader', -999) + 12; cnames = {i + 12: c['name'] for i, c in enumerate(cls)}; etags = I.element_tags(cls)
    isfull = lambda c: c in FULL_CLASSES or c.startswith(FULL_PREFIX)
    wanted = sorted(t for t, n in cnames.items() if t in etags)                      # all element classes: with only the admin classes wanted, ~0.03% of the headers are not accepted (f35: 6 of 22984)
    slim_tags = sorted(t for t in wanted if not isfull(cnames[t]))
    ENDX = len(cls)
    try: es = F.es_load(path)[0]
    except Exception: es = {}
    idlist = sorted(ids); rd = F.make_recdecoder(sch, W, es); rd.set_ids(idlist)
    import numpy as np
    idarr = np.array(idlist, dtype=np.uint64); N = len(idarr)
    seen = np.zeros(N, bool); a_cat = np.zeros(N, np.int64); a_ov = np.full(N, -1, np.int64); a_fam = np.full(N, -1, np.int64); a_bb = np.full((N, 6), np.nan, np.float32)
    a_cls = np.full(N, 65535, np.uint16); cnames_l = []; cn_ix = {}; full = {}; NOCAT = -(1 << 62)
    a_cat[:] = NOCAT
    prim = np.isin(idarr, np.array(sorted(prim_ids), dtype=np.uint64)); nprim = int(prim.sum()); del prim_ids
    STALL = int(os.environ.get('RVT_INFO_STALL', '0'))      # windows without a new header / admin record after which the scan stops early (0 = only when every element has its header and every admin record is found)
    admin_ids = set()
    found_ids = set()
    def got():       # element headers + class records found so far (both must stop growing / be complete before the scan may stop early)
        return int(seen.sum()) + len(found_ids)
    def alldone(): return int((seen & prim).sum()) >= nprim - 2 and admin_ids <= found_ids
    def slot(eid):
        k = int(np.searchsorted(idarr, eid)); return k if k < N and int(idarr[k]) == eid else -1
    pns = sorted(n for n in names if n.startswith('Partitions/'))      # same (lexicographic) order as rvt_fast._partitions: first-wins across partitions
    nwin = 0; maxwin = 0; nb = 0; stalled = 0; lastseen = 0; early = False
    items = [tuple(x) for x in _seg] if _seg else [(pn, 0, None) for pn in pns]
    total_pages = sum(-(-o.direntries[o._find(n)].size // PAGE_STORED) for n in pns)
    if not _seg and SEG_MB and total_pages * PAGE_STORED > SEG_MB * 1.5e6 and not os.environ.get('RVT_INFO_INPROC'):      # small files are decoded in this process
        # all decoding happens in worker processes (a fresh process resets allocator state; the master stays ~150 MB): big partitions are cut into SEG_MB segments, small ones grouped
        pp = int(SEG_MB * 1e6 // PAGE_STORED); jobs = []; cur = []; curpages = 0
        for pn in pns:
            sz = o.direntries[o._find(pn)].size; npg = -(-sz // PAGE_STORED)
            if npg > pp * 1.5:
                if cur: jobs.append(cur); cur = []; curpages = 0
                for lo in range(0, npg, pp): jobs.append([(pn, lo, lo + pp + SEG_EXTRA_PAGES)])
            else:
                cur.append((pn, 0, None)); curpages += npg
                if curpages >= pp: jobs.append(cur); cur = []; curpages = 0
        if cur: jobs.append(cur)
        import subprocess, pickle, tempfile
        WORKERS = max(1, int(os.environ.get('RVT_INFO_WORKERS', '1')))        # > 1 needs a memory cap of about 0.45 GB per worker + 0.2 GB
        code = "import sys, json; sys.path.insert(0, %r); from rvtballet import fastinfo as F; F._worker(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3])" % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        running = {}
        def launch(j):
            fd, op = tempfile.mkstemp(prefix='rvtinfo-seg-', suffix='.pkl'); os.close(fd)
            running[j] = (subprocess.Popen([sys.executable, '-c', code, path, json.dumps(jobs[j]), op], env=dict(os.environ, RVT_INFO_INPROC='1')), op)
        for ji, job in enumerate(jobs):
            for j in range(ji, min(len(jobs), ji + WORKERS)):
                if j not in running and not (os.environ.get('RVT_INFO_JOBS') and str(j + 1) not in os.environ['RVT_INFO_JOBS'].split(',')): launch(j)
            if os.environ.get('RVT_INFO_JOBS') and str(ji + 1) not in os.environ['RVT_INFO_JOBS'].split(','): continue      # debugging: run only these jobs
            if alldone():
                for pr, op in running.values():
                    pr.kill()
                    try: os.remove(op)
                    except OSError: pass
                early = True; say('all headers and admin records found: %d of %d jobs skipped' % (len(jobs) - ji, len(jobs))); break
            proc, outp = running.pop(ji)
            try:
                rc = proc.wait()
                if rc != 0: raise RuntimeError('worker for %s failed (exit %d)' % (job[0][0], rc))
                part = pickle.load(open(outp, 'rb'))
            finally:
                try: os.remove(outp)
                except OSError: pass
            nwin += part['windows']; maxwin = max(maxwin, part['maxwin']); nb += part['nb']; STATS['crc_bad'] += part.get('crc_bad', 0); STATS['members'] += part.get('members', 0)
            sl = part['idx']; new = ~seen[sl]; t = sl[new]
            seen[t] = True; a_cat[t] = part['cat'][new]; a_ov[t] = part['ov'][new]; a_fam[t] = part['fam'][new]; a_bb[t] = part['bb'][new]
            for j, cc_ in enumerate(part['cls'][new]):
                if cc_ == 65535: continue
                nmx = part['cls_names'][int(cc_)]; ci = cn_ix.get(nmx)
                if ci is None: ci = cn_ix[nmx] = len(cnames_l); cnames_l.append(nmx)
                a_cls[t[j]] = ci
            for k_, v_ in part['full'].items():
                if k_ not in full: full[k_] = v_
            found_ids |= part['found']; admin_ids |= part['admin']
            say('job %d/%d (%s%s): %d new headers, %d windows, %.1fs' % (ji + 1, len(jobs), job[0][0], '+%d' % (len(job) - 1) if len(job) > 1 else ' pages %s-%s' % (job[0][1], job[0][2]), len(t), part['windows'], time.time() - t0))
            if progress: progress(ji + 1, len(jobs), int(seen.sum()))
        items = []
    for pi, (pn, lo_p, hi_p) in enumerate(items):
        stalled = 0; lastseen = got(); p0 = lastseen; pearly = False
        if not _seg and alldone(): early = True; break
        for chunk, fin in windows(chain_blocks(o, pn, lo_page=lo_p, hi_page=hi_p)):
            if (not _seg and alldone()) or (STALL and stalled >= STALL and lastseen > p0): early = pearly = True; break
            nwin += 1; maxwin = max(maxwin, len(chunk)); nb += len(chunk)
            if os.environ.get('RVT_INFO_TRACE'): say('win %d %s: %.1f MB, hdr %d, rss %d MB' % (nwin, pn, len(chunk) / 1e6, int(seen.sum()), _rss_mb()))
            r = _extract_groups(rd, chunk, wanted, EH, slim_tags, idlist)
            for (eid, c), rec in r[0]:
                if isfull(c) and rec.get('fields') and (eid, c) not in full: full[(eid, c)] = _reduce(c, rec); found_ids.add(eid)
            if r[1]:
                _ea = np.array([int(e) for e, _ in r[1]], dtype=np.uint64); _ks = np.searchsorted(idarr, _ea); _ks[_ks >= N] = N - 1
                _ok = idarr[_ks] == _ea; _slots = np.where(_ok, _ks, -1).tolist()      # one vectorised lookup per window instead of one searchsorted per header
            else: _slots = []
            for (eid, h), k in zip(r[1], _slots):
                if k < 0 or seen[k]: continue
                seen[k] = True
                cid = h.get('m_categroryId'); ov = h.get('m_ownerViewId'); fam = h.get('m_familyId')
                pb = h.get('m_pBBox'); pb = pb.get('obj', pb) if isinstance(pb, dict) else pb
                mm = pb.get('m_minmax') if isinstance(pb, dict) else None
                bb = (tuple(map(float, mm[0])) + tuple(map(float, mm[1]))) if mm and len(mm) == 2 else None
                cd = h.get('m_classDef'); cd = cd.get('m_ref') if isinstance(cd, dict) else cd         # class tag of the element (tag - 12 = schema index; 25593 of 25595 equal the decoded record class)
                if isinstance(cd, int) and 12 <= cd < 12 + ENDX:
                    nmx = cls[cd - 12]['name']; ci = cn_ix.get(nmx)
                    if ci is None: ci = cn_ix[nmx] = len(cnames_l); cnames_l.append(nmx)
                    a_cls[k] = ci
                    if isfull(nmx): admin_ids.add(eid)
                if cid is not None and _plausible(cid, W): a_cat[k] = _sc(cid, W)         # a garbage header (e.g. id 0 decoded from zero bytes) must not invent categories
                if ov is not None and _plausible(ov, W): a_ov[k] = _sc(ov, W)
                if fam is not None and _plausible(fam, W): a_fam[k] = _sc(fam, W)
                if bb: a_bb[k] = bb
            del r, chunk; _trim()
            cur = got(); stalled = 0 if cur > lastseen else stalled + 1; lastseen = cur
        if pearly: say('%s: stopped early' % pn)
        say('partition %s (%d/%d): %d element headers, %.1fs' % (pn, pi + 1, len(items), int(seen.sum()), time.time() - t0))
    if _seg:
        sl = np.nonzero(seen)[0]; import pickle
        pickle.dump({'idx': sl, 'cat': a_cat[sl], 'ov': a_ov[sl], 'fam': a_fam[sl], 'bb': a_bb[sl], 'cls': a_cls[sl], 'cls_names': cnames_l, 'full': full, 'found': found_ids, 'admin': admin_ids,
                     'windows': nwin, 'maxwin': maxwin, 'nb': nb, 'crc_bad': STATS['crc_bad'], 'members': STATS['members']}, open(_out, 'wb'), protocol=5)
        return None
    res = {'stats': {'damaged_members': STATS['crc_bad'], 'members': STATS['members'], 'stopped_early': early, 'primary_elements': nprim, 'primary_with_header': int((seen & prim).sum()), 'partitions': len(pns), 'windows': nwin, 'max_window_mb': round(maxwin / 1e6, 1), 'decoded_mb': round(nb / 1e6), 'elements_with_header': int(seen.sum()), 'seconds': round(time.time() - t0, 2)}}
    cat = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'category_names.json')))
    from . import categories as CT
    a_cat = CT.resolve(a_cat, a_cls, np.array(cnames_l or ['']), idarr, full, W)
    u, n = np.unique(a_cat[seen], return_counts=True)
    cc = collections.Counter()
    for v, c in zip(u.tolist(), n.tolist()): cc[cat.get(str(v), 'cat %s' % (v if v != NOCAT else 'none'))] += c
    res['counts'] = dict(cc.most_common())
    u, n = np.unique(a_cls[a_cls != 65535], return_counts=True)
    res['class_counts'] = dict(sorted(((cnames_l[int(i)], int(c)) for i, c in zip(u, n)), key=lambda t: -t[1]))
    res['view_owned'] = int(((a_ov != -1) & seen).sum())
    S_ = E.S_
    recs = {}; by = collections.defaultdict(list)
    for (eid, c), r in full.items():
        if eid in owner and c in ('Level', 'Grid', 'RoomElem', 'DBViewDrafting'): continue     # copies owned by groups / assemblies (rvt_entities.parse)
        by[c].append(r); recs.setdefault(eid, r)
    nm = lambda i: (recs[i]['fields'].get('m_text') or recs[i]['fields'].get('m_viewName') or recs[i]['fields'].get('m_name') or '') if i in recs else ''
    res['levels'] = sorted([{'id': r['id'], 'name': r['fields'].get('m_text', ''), 'elevation_ft': (S_(r['fields'], 'm_pSurface', 'm_origin') or [None] * 3)[2]} for r in by['Level']],
                           key=lambda l: (l['elevation_ft'] is None, l['elevation_ft'] if l['elevation_ft'] is not None else 0, l['name'], l['id']))      # deterministic ties (diffable)
    res['grids'] = sorted(r['fields'].get('m_text', '') for r in by['Grid'])
    views = []; sheets = []
    for c, lst in by.items():
        if not c.startswith('DBView'): continue
        for r in lst:
            f = r['fields']; n = f.get('m_viewName')
            if n is None: continue
            if c == 'DBViewDrafting' and f.get('m_sheetNumber'):
                sheets.append({'id': r['id'], 'number': f.get('m_sheetNumber'), 'name': n, 'issue_date': f.get('m_issueDate'), 'drawn_by': f.get('m_drawnBy'), 'approved_by': f.get('m_approvedBy'), 'revision_ids': [int(v) for v in (f.get('m_explicitlyPresentRevisionIds') or []) if isinstance(v, (int,)) or hasattr(v, '__int__')],
                               'viewports': [int(v) for v in (f.get('m_sheetViewportElemIds') or [])]})
            else: views.append({'id': r['id'], 'name': n, 'class': c, 'template': bool(f.get('m_isTemplate')), 'scale': f.get('m_scale')})
    vp = {r['id']: int(r['fields'].get('m_dbViewId', -1)) for r in by['Viewport']}
    on_sheet = collections.defaultdict(list)             # 2023+ files: a sheet lists no viewports; each Viewport element is owned by its sheet (ElementHeader.m_ownerViewId)
    for v, dv in vp.items():
        k = slot(v)
        if k >= 0 and a_ov[k] not in (-1, 0) and seen[k]: on_sheet[int(a_ov[k])].append(dv)
    for s in sheets:
        ids_ = [vp[v] for v in s.pop('viewports') if v in vp]
        s['views'] = [nm(d) for d in ids_ if d in recs] if ids_ else sorted(nm(d) for d in on_sheet.get(s['id'], []) if d in recs)
    res['views'] = sorted(views, key=lambda v: (v['class'], v['name'], v['id'])); res['sheets'] = sorted(sheets, key=lambda s: (str(s['number']), s['id']))
    revs = {r['id']: r['fields'] for r in by['ProjectRevision']}
    res['revisions'] = sorted(({'id': i, 'sequence': f.get('m_sequenceNumber'), 'number': f.get('m_numberStr'), 'description': f.get('m_description'), 'date': f.get('m_date'), 'issued_by': f.get('m_issuedBy')} for i, f in revs.items()), key=lambda r: (r['sequence'] is None, r['sequence'] or 0, r['id']))
    for sh in res['sheets']: sh['revisions'] = [{'number': revs[i].get('m_numberStr'), 'description': revs[i].get('m_description'), 'date': revs[i].get('m_date')} for i in sorted(sh.get('revision_ids') or [], key=lambda i: revs.get(i, {}).get('m_sequenceNumber') or 0) if i in revs]
    res['phases'] = [r['fields'].get('m_name') for r in by['ProjectPhase']]
    if want_elements:
        m = seen; res['arrays'] = {'id': idarr[m], 'cat': a_cat[m], 'owner_view': a_ov[m], 'family': a_fam[m], 'bbox': a_bb[m], 'cls': a_cls[m], 'cls_names': np.array(cnames_l or [''], dtype=str)}
    return res


def _worker(path, items, out):
    scan(path, _seg=items, _out=out)
