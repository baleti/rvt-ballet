"""rvt-ballet targeted queries on big .rvt files: decode ONLY the classes a query needs, cold, no index.

Why it is fast (measured on a 984 MB project file, see docs/rvt-fast-query.md):
- one fork pool: schema, ElemTable ids and the Rust RecDecoder are built ONCE in the master and inherited by the workers (fastinfo starts a fresh
  interpreter per 96 MB job: ~3 s CPU each);
- tasks are runs of whole gzip segments taken from the segment-header walk (elemindex.Part.segments, no inflate), so the load is balanced and a
  task is small; each worker reads its stored bytes with os.pread over contiguous sector runs (own fd, no shared file offset after fork);
- the Rust decoder is asked for the query classes only and for no ElementHeader (ElementHeader trees are what made the generic scan slow);
  headers are decoded in a second pass restricted to the few ids that need one (only_ids).
Read-only: the file is opened once with O_RDONLY and never written; a file that changes while it is read raises FileChanged instead of returning an answer.
"""
import os, sys, struct, zlib, time, collections
_T0 = time.time()

PAGE_STORED = 65249; PAGE_PAYLOAD = 64896
TASK_MB = float(os.environ.get('RVT_Q_TASK_MB', '8'))          # decoded MB per task (plus the overlap)
OVL = int(os.environ.get('RVT_Q_OVERLAP_KB', '1024')) << 10     # decoded bytes of the following segments appended to a task (a record straddling the task end is decoded whole)
_G = {}
# segment header word 4 is a channel: 101 = ElementHeaders, 102 = element records, 103 = geometry/bulk blobs (each channel carries the same sequence of
# sub-records, measured on a 984 MB 2024 file: 2.61M per channel, 101 is the first contiguous block of every partition). No query class record and no
# ElementHeader sits in 103 (all query outputs identical without it, 984 MB file + samples), so the walk keeps 101+102 only: 4.03 -> 2.35 GB to inflate.
# RVT_Q_CHANNELS=all keeps every segment (old behaviour); a comma list picks channels.
_ch = os.environ.get('RVT_Q_CHANNELS', '101,102')
CHANNELS = None if _ch == 'all' else frozenset(int(x) for x in _ch.split(','))
KNOWN_CH = frozenset((101, 102, 103))
SPLIT = os.environ.get('RVT_Q_SPLIT', '1') == '1'      # channel-pure tasks (101: header candidates only, 102: class scan only)


def _paths():
    from . import rvtfile as RF
    RF._paths()


from .stable import FileChanged            # one exception type for every torn-read check (stable.py: fingerprint/quiet period/snapshot)


def _stamp(st): return (st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev)


def consistent(G=None):
    """raise FileChanged when the file under the query differs from the one opened at _setup: size/mtime of the open handle (written in place) or of the
    path (replaced by a rename, the usual way an application saves). Called after every query, so an answer is only returned when the file did not change
    between opening and the last read. Without a stat change, gzip CRC failures are reported as damage (G['damaged'])."""
    G = G or _G; st0 = G.get('st0')
    if st0 is None: return
    try: a = _stamp(os.fstat(G['fd'])); b = _stamp(os.stat(G['path']))
    except OSError as ex: raise FileChanged(G['path'], 'cannot stat it any more: %s' % ex)
    if a[:2] != st0[:2]: raise FileChanged(G['path'], 'size/modification time of the open file changed')
    if b[:2] != st0[:2] or (b[2] and st0[2] and b[2] != st0[2]): raise FileChanged(G['path'], 'the path now points at a different file')


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
        hdr = i - 24; rd = s._small_reader(fd); allsegs = []; unknown = False
        N = _native() if NATIVE and s.small is None else None
        if N is not None:
            rows = _native_walk_all(N, s, hdr, T)
            if rows is not None:
                for off_, st_, dl_, ch_, _w0 in rows:
                    if ch_ not in KNOWN_CH: unknown = True
                    allsegs.append((off_, st_, dl_, ch_))
                    if CHANNELS is None or ch_ in CHANNELS:
                        segs.append((off_, st_, dl_, ch_))
                        if cb and len(segs) % every == 0 and not unknown: cb(segs)
                hdr = None
        while hdr is not None and hdr + 24 <= T:
            if N is not None:                   # C walk over the mmap (same tests); stops where a header does not verify, the Python step below resyncs
                k, hdr2, arr = _native_walk(N, s, hdr, T)
                if k:
                    for off_, st_, dl_, ch_, _w0 in arr:
                        if ch_ not in KNOWN_CH: unknown = True
                        allsegs.append((off_, st_, dl_, ch_))
                        if CHANNELS is None or ch_ in CHANNELS:
                            segs.append((off_, st_, dl_, ch_))
                            if cb and len(segs) % every == 0 and not unknown: cb(segs)
                    hdr = hdr2; continue
            b = rd(hdr, 28)
            if len(b) == 28:
                w = struct.unpack('<6I', b[:24])
                if b[24:28] == GZ and 18 <= w[2] and hdr + 24 + w[2] <= T and w[0] < 16 and w[3] > 0:
                    if w[4] not in KNOWN_CH: unknown = True
                    allsegs.append((hdr + 24, w[2], w[3], w[4]))
                    if CHANNELS is None or w[4] in CHANNELS: segs.append((hdr + 24, w[2], w[3], w[4]))
                    hdr += 24 + w[2]
                    if cb and len(segs) % every == 0 and not unknown: cb(segs)
                    continue
            if N is not None:
                r_ = _native_resync(N, s, hdr, T)
                if r_ != -2: hdr = None if r_ < 0 else r_; continue
            hdr = s._resync(fd, hdr, T)
        if unknown or (allsegs and CHANNELS is not None and not segs):
            # a channel value outside 101/102/103 (other Revit versions / layouts): no channel logic at all, the old walk result (3-tuples, all segments).
            # Early tasks already sent from a prefix would then differ from plan(): walk_and_decode asserts on that (loud, never silent)
            return [x[:3] for x in allsegs]
        return segs
    def _small_reader(s, fd):
        """payload bytes [a, a+n) for small n: one slice of an mmap of the file when the bytes sit inside one page payload and one sector (the common case),
        else payload() (same bytes). The walk reads 28 bytes per segment: a 64 KB pread each was 0.4-0.7 s of serial master time on a 984 MB file."""
        if s.small is not None: return lambda a, n: s.payload(fd, a, a + n)
        import mmap
        try: m = mmap.mmap(fd, 0, prot=mmap.PROT_READ)
        except (ValueError, OSError, AttributeError): return lambda a, n: s.payload(fd, a, a + n)
        ss = s.ss; ch = s.chain; P = PAGE_PAYLOAD; PS = PAGE_STORED
        def rd(a, n):
            pg, po = divmod(a, P)
            if po + n <= P:
                st = pg * PS + po; k, so = divmod(st, ss)
                if so + n <= ss and k < len(ch):
                    o = (ch[k] + 1) * ss + so; return m[o:o + n]
            return s.payload(fd, a, a + n)
        return rd
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
            L.libdeflate_crc32.restype = ctypes.c_uint32; L.libdeflate_crc32.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_size_t]
            lib = (L, ctypes); break
    _LD.append(lib); return lib


def _inflate_run_raw(buf, a, segs, sizes_out=None, bad_out=None):
    """inflated bytes of consecutive segments [(payload offset, stored_len, x)], `buf` = payload bytes from offset `a`. A segment's stored bytes are
    [10-byte gzip header][deflate][CRC32][ISIZE][8-byte footer]: libdeflate inflates straight into one buffer sized from the ISIZE fields (an ISIZE that does
    not match the inflated size falls back to zlib for that segment)"""
    lib = _libdeflate()
    if lib is None:
        parts = []
        for off, ln, *_ in segs:
            try: x = _inflate(buf[off - a: off - a + ln])
            except zlib.error: x = b''
            if bad_out is not None and (ln < 34 or zlib.crc32(x) & 0xffffffff != struct.unpack_from('<I', buf, off - a + ln - 16)[0]): bad_out.append(off)
            parts.append(x)
        if sizes_out is not None: sizes_out.extend(len(x) for x in parts)
        return b''.join(parts)
    L, C = lib; d = _G.get('ldd')
    if d is None or _G.get('ldd_pid') != os.getpid(): d = _G['ldd'] = L.libdeflate_alloc_decompressor(); _G['ldd_pid'] = os.getpid()
    sizes = [struct.unpack_from('<I', buf, off - a + ln - 12)[0] if ln >= 34 else 0 for off, ln, *_ in segs]
    out = bytearray(sum(sizes)); ob = C.addressof((C.c_char * max(1, len(out))).from_buffer(out)) if out else 0
    ib = C.cast(C.c_char_p(buf), C.c_void_p).value; ai = C.c_size_t(); ao = C.c_size_t(); o = 0; fix = []
    for i, ((off, ln, *_), sz) in enumerate(zip(segs, sizes)):
        r = L.libdeflate_deflate_decompress_ex(d, ib + off - a + 10, ln - 10, ob + o, sz, C.byref(ai), C.byref(ao)) if sz else 1
        if r != 0 or ao.value != sz: fix.append(i)
        o += sz
    if bad_out is not None:              # gzip CRC32 of every segment (libdeflate_crc32): a torn or damaged segment never decodes silently
        o = 0
        for i, ((off, ln, *_), sz) in enumerate(zip(segs, sizes)):
            if i not in fix and L.libdeflate_crc32(0, ob + o, sz) != struct.unpack_from('<I', buf, off - a + ln - 16)[0]: bad_out.append(off)
            o += sz
    if not fix:
        if sizes_out is not None: sizes_out.extend(sizes)
        return bytes(out)
    parts = []; o = 0                         # rare: rebuild with zlib for the odd segments
    for i, ((off, ln, *_), sz) in enumerate(zip(segs, sizes)):
        if i in fix:
            try: x = _inflate(buf[off - a: off - a + ln])
            except zlib.error: x = b''
            if bad_out is not None and (ln < 34 or zlib.crc32(x) & 0xffffffff != struct.unpack_from('<I', buf, off - a + ln - 16)[0]): bad_out.append(off)
        else: x = bytes(out[o:o + sz])
        parts.append(x); o += sz
    if sizes_out is not None: sizes_out.extend(len(x) for x in parts)
    return b''.join(parts)


RUN_PAD = 8


def inflate_run(buf, a, segs, sizes_out=None, bad_out=None, reader=None):
    """_inflate_run_raw, plus RUN_PAD zero bytes in front of every run of physically adjacent segments when the segments carry a channel (per-channel
    tasks gather one channel's runs from many (101, 102, 103) triples). The record at the start of a run has no A prefix; the Rust candidate scan finds it
    only with more than its own 4 pad bytes in front. Each pad counts in the size of the segment after it, so a position still maps to the right segment.
    bad_out gets the offset of every segment whose gzip CRC32 fails (checked per run by _inflate_run_raw)."""
    if not segs or len(segs[0]) < 4:
        if buf is None: a = segs[0][0]; buf = reader(a, segs[-1][0] + segs[-1][1])
        return _inflate_run_raw(buf, a, segs, sizes_out, bad_out)
    runs = []; st = 0
    for i in range(1, len(segs) + 1):
        if i == len(segs) or segs[i][0] != segs[i - 1][0] + segs[i - 1][1] + 24: runs.append((st, i)); st = i
    parts = []; pad = bytes(RUN_PAD)
    for x, y in runs:
        sz = [] if sizes_out is not None else None
        if reader is not None:
            ra = segs[x][0]; parts.append(pad); parts.append(_inflate_run_raw(reader(ra, segs[y - 1][0] + segs[y - 1][1]), ra, segs[x:y], sz, bad_out))
        else: parts.append(pad); parts.append(_inflate_run_raw(buf, a, segs[x:y], sz, bad_out))
        if sz is not None: sz[0] += RUN_PAD; sizes_out.extend(sz)
    return b''.join(parts)


def _chan_groups(segs):
    """global segment indices grouped by channel, each group in stream order. A partition is a sequence of (101, 102, 103) triples (one big base triple,
    then one small triple per incremental save: 4324 triples in the biggest partition of a 984 MB file); each channel is ONE logical stream across the
    triples; tasks are planned over one channel's segments, never across channels (inflate_run pads the start of every run)."""
    if not segs or len(segs[0]) < 4: return [list(range(len(segs)))]
    g = {}
    for i, sg in enumerate(segs): g.setdefault(sg[3], []).append(i)
    return [g[c] for c in sorted(g)]


def plan(pi, pn, segs, task_mb=None, ovl=None, final_only=False):
    """decode tasks of one partition in stream order: (key, pn, segment list, number of main segments); the tail of the list is the overlap.
    key = (pi, global index of the first segment); tasks are planned over one channel's segments (_chan_groups). final_only: only tasks that later
    segments cannot change (main and overlap both full)."""
    tasks = []; per = (task_mb or TASK_MB) * 1e6; OVL = ovl or globals()['OVL']
    for idx in _chan_groups(segs):
        N = len(idx); k = 0
        while k < N:
            j = k; n = 0
            while j < N and (n < per or j == k): n += segs[idx[j]][2]; j += 1
            m = j; ov = 0
            while m < N and ov < OVL: ov += segs[idx[m]][2]; m += 1
            if final_only and (n < per or ov < OVL): break
            tasks.append(((pi, idx[k]), pn, [segs[x] for x in idx[k:m]], j - k)); k = j
    return tasks


def _winit():
    if _G.get('fd') is None: _G['fd'] = os.open(_G['path'], os.O_RDONLY)      # normally inherited from _setup (one handle: every worker reads the same file version)
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
    ch = segs[0][3] if len(segs[0]) > 3 else None
    if SPLIT and ch == 101 and not note_eh and not hdr_ids:        # header channel, nothing asked of it: do not even inflate
        return job[:2], ([], [], None, (time.process_time() - c0, time.time() - w0, os.getpid(), 0))
    from . import rvtfile as FI
    rd = _G['rd']; recs = []; ehs = []; ehc = None
    specs = wanted if isinstance(wanted, list) and wanted and isinstance(wanted[0], dict) else ([{'tags': wanted}] if wanted else [])
    if SPLIT and ch == 101 and not hdr_ids: specs = []            # ElementHeader channel: no class record to find
    if SPLIT and ch == 102: note_eh = False                        # record channel: no ElementHeader
    nat = None; chunk = None; fr = None; bad = []
    if NATIVE and SPLIT and not hdr_ids and ch in (101, 102) and S.small is None and (specs if ch == 102 else note_eh):
        nat = _native_task(S, segs, nmain, ch, bad)
        if nat is None and DEBUG: sys.stderr.write('NATIVE fallback %r %s\n' % (key, _G.pop('why', '?')))
        if nat is None: bad = []
    if nat is None:
        sizes = []; chunk = inflate_run(None, None, segs, sizes, bad, reader=lambda x, y: S.payload(fd, x, y))
        if FRAME and SPLIT and ch == 102 and specs:
            fr = frame_records(chunk, sizes, segs, nmain, _G['W'])
            if fr is None and DEBUG: sys.stderr.write('FRAME fallback %r %s\n' % (key, _G.pop('why', '?')))
    bad = [x for x in bad if x <= segs[nmain - 1][0]] if 0 < nmain <= len(segs) else bad      # a segment counts in the task that owns it (overlap segments belong to the next task)
    loc = None
    for sp in specs:              # {'tags', 'mode': 'fi' (fastinfo._reduce) | 'lite' (_lite), 'full': no-STOP decoder (type names), 'only': ids}
        if sp.get('locate'):      # locator only: ids of the records with these tags whose id lies in this task's main part (no decode)
            import numpy as np
            if nat is not None:
                rv = nat['recs'][:4 * nat['k']].reshape(-1, 4); loc = np.unique(rv[np.isin(rv[:, 3], np.asarray(sp['tags'], np.int64)), 2].astype(np.uint64))
            elif fr is not None:
                tg = set(sp['tags']); loc = np.unique(np.asarray([e for (a_, b_, e, t) in fr if t in tg], np.uint64))
            continue
        d_ = _G['rd_full'] if sp.get('full') else rd
        okid = None               # framed paths: a decode is kept only for an id the framing put in the mini buffer (zero pads and record bodies can
                                  # hold false candidates: id-0 rows on the 984 MB file)
        if nat is not None:
            mini = _native_gather(nat, sp['tags'], sp.get('only'))
            r = d_.extract_chunk(mini, sp['tags'], -1, sp.get('only'), []) if mini else ([], [])
            import numpy as np
            rv = nat['recs'][:4 * nat['k']].reshape(-1, 4); okid = set(rv[np.isin(rv[:, 3], np.asarray(list(sp['tags']), np.int64)), 2].tolist())
        elif fr is not None:
            tg = set(sp['tags']); on = set(int(x) for x in sp['only']) if sp.get('only') is not None else None
            mini = b''.join(PAD8 + chunk[a_:b_] for (a_, b_, e, t) in fr if t in tg and (on is None or e in on))
            r = d_.extract_chunk(mini, sp['tags'], -1, sp.get('only'), []) if mini else ([], [])
            okid = {e for (a_, b_, e, t) in fr if t in tg}
        else:
            r = d_.extract_chunk(chunk, sp['tags'], -1, sp.get('only'), [])
        lite = sp.get('mode') == 'lite'
        for (eid, c), rec in r[0]:
            if okid is not None and int(eid) not in okid or int(eid) == 0: continue       # id 0 is never an element: a decode at a zero pad
            if rec.get('fields'): recs.append(((int(eid), c), _lite(c, rec) if lite and c not in FI_REDUCED else FI._reduce(c, rec)))
    if note_eh: ehc = nat['ehc'] if nat is not None else _eh_candidate_ids(chunk, sizes)
    if hdr_ids:
        allh = hdr_ids == 'all'
        r = rd.extract_chunk(chunk, [], _G['EH'], None if allh else hdr_ids, [])
        for eid, h in r[1]:
            cd = h.get('m_classDef'); cd = cd.get('m_ref') if isinstance(cd, dict) else cd
            t = (h.get('m_categroryId'), h.get('m_ownerViewId'), h.get('m_familyId'), cd)
            if allh:
                pb = _ob(h.get('m_pBBox')); mm = pb.get('m_minmax') if isinstance(pb, dict) else None
                t += ((tuple(map(float, mm[0])) + tuple(map(float, mm[1]))) if mm and len(mm) == 2 else None,)
            ehs.append((int(eid), t))
        del r
    return job[:2], (recs, ehs, ehc, (time.process_time() - c0, time.time() - w0, os.getpid(), len(bad)), loc)


NATIVE = os.environ.get('RVT_Q_NATIVE', '1') == '1'           # C helper _rvtframe.so (inflate from mmap, 102 framing, walk); missing -> Python
DEBUG = bool(os.environ.get('RVT_Q_DEBUG'))
LOCATE = os.environ.get('RVT_Q_LOCATE', '1') == '1'
_NAT = {}


def _cpu_v3():
    """_rvtframe.so is built -march=x86-64-v3: on a CPU without these flags it would die with SIGILL on first call instead of falling back; check first"""
    if os.environ.get("RVT_Q_CPUFLAGS") is not None: fl = set(os.environ["RVT_Q_CPUFLAGS"].split())          # test hook
    else:
        try: fl = set(next(l for l in open("/proc/cpuinfo") if l.startswith("flags")).split())
        except Exception: return False
    return {"avx2", "bmi1", "bmi2", "fma", "movbe", "abm"} <= fl or {"avx2", "bmi1", "bmi2", "fma", "movbe", "lzcnt"} <= fl


def _native():
    """ctypes handle on _rvtframe.so (next to this file) + libdeflate; None when either is missing (the Python path is used)"""
    key = (os.getpid(), _G.get('gen'))           # one mmap/chain/id cache per _setup: a second query in the same process (another file, or the same one after a save) must not see the first one's
    if 'lib' in _NAT and _NAT.get('key') == key: return _NAT['lib']
    old = _NAT.get('lib')
    if old is not None and _NAT.get('key', (0,))[0] == os.getpid():
        try: old['mv'] = None; old['mm'].close()
        except Exception: pass
    lib = None; ld = _libdeflate()
    so = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_rvtframe.so')
    if ld is not None and os.path.exists(so) and _cpu_v3():
        import ctypes as C, mmap
        try:
            L = C.CDLL(so)
            for f in ('inflate_task', 'frame102', 'gather', 'eh_candidates'): getattr(L, f).restype = C.c_int64
            P = C.c_void_p; I = C.c_int64
            L.inflate_task.argtypes = [P, I, P, I, I, P, I, P, I, P, P, I, P, P, P, P]
            L.frame102.argtypes = [P, I, P, I, I, P, C.c_int, C.c_uint64, C.c_int, P, I]
            L.gather.argtypes = [P, P, I, P, P, I, P, I]
            L.eh_candidates.argtypes = [P, I, C.c_int, C.c_int, P, I, P, I, P, I]
            LD, _ = ld
            fnp = C.cast(LD.libdeflate_deflate_decompress_ex, C.c_void_p).value
            crcp = C.cast(LD.libdeflate_crc32, C.c_void_p).value
            dec = LD.libdeflate_alloc_decompressor()
            fd = os.open(_G['path'], os.O_RDONLY); fsize = os.fstat(fd).st_size
            mm = mmap.mmap(fd, 0, prot=mmap.PROT_READ); os.close(fd)
            import numpy as np
            mv = np.frombuffer(mm, np.uint8); base = mv.ctypes.data
            lib = dict(L=L, C=C, np=np, fnp=fnp, crcp=crcp, dec=dec, mm=mm, mv=mv, base=base, fsize=fsize, chains={},
                       tmp=np.empty(4 << 20, np.uint8), buf=np.empty(0, np.uint8), ids=np.ascontiguousarray(_G['ids'], np.uint64))
        except Exception as ex:
            sys.stderr.write('native helper unavailable: %r\n' % (ex,)); lib = None
    _NAT.clear(); _NAT.update(lib=lib, key=key); return lib


def _native_resync(N, S, a, T):
    L = N['L']; C = N['C']; np = N['np']
    if not hasattr(L.resync_segments, '_set'):
        L.resync_segments.restype = C.c_int64; P = C.c_void_p; I = C.c_int64
        L.resync_segments.argtypes = [P, I, P, I, I, I, I, P]; L.resync_segments._set = 1
    if 'rbuf' not in N: N['rbuf'] = np.empty((4 << 20) + 64 + (1 << 14), np.uint8)
    chain = N['chains'].get(id(S))
    if chain is None: chain = N['chains'][id(S)] = np.ascontiguousarray(np.array(S.chain, np.int32))
    return L.resync_segments(N['base'], N['fsize'], chain.ctypes.data, len(chain), S.ss, a, T, N['rbuf'].ctypes.data)


def _native_walk_all(N, S, hdr, T):
    L = N['L']; C = N['C']; np = N['np']
    if not hasattr(L.walk_all, '_set'):
        L.walk_all.restype = C.c_int64; P = C.c_void_p; I = C.c_int64
        L.walk_all.argtypes = [P, I, P, I, I, I, I, P, I, P]; L.walk_all._set = 1
    if 'rbuf' not in N: N['rbuf'] = np.empty((4 << 20) + 64 + (1 << 14), np.uint8)
    chain = N['chains'].get(id(S))
    if chain is None: chain = N['chains'][id(S)] = np.ascontiguousarray(np.array(S.chain, np.int32))
    cap = S.total // 42 + 64; out = np.empty(5 * cap, np.int64)
    k = L.walk_all(N['base'], N['fsize'], chain.ctypes.data, len(chain), S.ss, hdr, T, out.ctypes.data, cap, N['rbuf'].ctypes.data)
    return None if k < 0 else out[:5 * k].reshape(-1, 5).tolist()


def _native_walk(N, S, hdr, T):
    np = N['np']; L = N['L']; C = N['C']
    if not hasattr(L.walk_segments, '_set'):
        L.walk_segments.restype = C.c_int64; P = C.c_void_p; I = C.c_int64
        L.walk_segments.argtypes = [P, I, P, I, I, I, I, P, I, P]; L.walk_segments._set = 1
    ck = id(S); chain = N['chains'].get(ck)
    if chain is None: chain = N['chains'][ck] = np.ascontiguousarray(np.array(S.chain, np.int32))
    cap = 1 << 16; out = np.empty(5 * cap, np.int64); nx = np.zeros(1, np.int64)
    k = L.walk_segments(N['base'], N['fsize'], chain.ctypes.data, len(chain), S.ss, hdr, T, out.ctypes.data, cap, nx.ctypes.data)
    return k, int(nx[0]), out[:5 * k].reshape(-1, 5).tolist()


def _native_task(S, segs, nmain, ch, bad):
    """inflate + (102) frame or (101) ElementHeader candidates in C, straight from an mmap of the file; None on any failure (Python path)"""
    N = _native()
    if N is None: return None
    np = N['np']; L = N['L']
    ck = id(S); chain = N['chains'].get(ck)
    if chain is None: chain = N['chains'][ck] = np.ascontiguousarray(np.array(S.chain, np.int32))
    sa = np.array([(x[0], x[1]) for x in segs], np.int64)
    need = int(sum(x[2] for x in segs) + 8 * len(segs) + 4096)
    if len(N['buf']) < need: N['buf'] = np.empty(int(need * 1.3), np.uint8)
    buf = N['buf']; sizes = np.zeros(len(segs), np.int64); badf = np.zeros(len(segs), np.uint8)
    if int(sa[:, 1].max()) > len(N['tmp']): N['tmp'] = np.empty(int(sa[:, 1].max()) + 4096, np.uint8)
    n = L.inflate_task(N['base'], N['fsize'], chain.ctypes.data, len(chain), S.ss, sa.ctypes.data, len(segs), buf.ctypes.data, len(buf),
                       sizes.ctypes.data, N['tmp'].ctypes.data, len(N['tmp']), N['dec'], N['fnp'], N['crcp'], badf.ctypes.data)
    if n < 0: _G['why'] = 'inflate %d' % n; return None
    bad.extend(int(segs[i][0]) for i in np.flatnonzero(badf).tolist())      # gzip CRC32 of every segment (libdeflate_crc32 in C): same rule as inflate_run
    bounds = np.zeros(len(segs) + 1, np.int64); np.cumsum(sizes, out=bounds[1:])
    if ch == 101:
        cap = max(1024, n // 64); out = np.empty(2 * cap, np.int64)
        k = L.eh_candidates(buf.ctypes.data, n, _G['EH'], _G['W'], N['ids'].ctypes.data, len(N['ids']), bounds.ctypes.data, len(segs), out.ctypes.data, cap)
        if k < 0: _G['why'] = 'eh cap'; return None
        v = out[0:2 * k:2].astype(np.uint64); sg = out[1:2 * k:2].astype(np.int32); o = np.lexsort((sg, v))
        return {'ehc': (v[o], sg[o])}
    cap = n // 20 + 64; recs = np.empty(4 * cap, np.int64)
    k = L.frame102(buf.ctypes.data, n, bounds.ctypes.data, len(segs), nmain, sa.ctypes.data, 12 + len(_G['cls']), _id_top(), _G['W'], recs.ctypes.data, cap)
    if k < 0: _G['why'] = 'frame %d' % k; return None
    return {'buf': buf, 'n': n, 'recs': recs, 'k': k}


def _native_gather(nat, tags, only):
    N = _NAT['lib']; np = N['np']
    mask = np.zeros(65536, np.uint8); mask[np.asarray(list(tags), np.int64)] = 1
    on = np.unique(np.asarray([int(x) for x in only], np.uint64)) if only is not None else np.zeros(1, np.uint64)
    rv = nat['recs'][:4 * nat['k']].reshape(-1, 4)
    tot = int((rv[:, 1] - rv[:, 0]).sum() + 8 * len(rv)) + 16
    out = np.empty(tot, np.uint8)
    if only is not None and not len(on): return b''
    m = N['L'].gather(nat['buf'].ctypes.data, nat['recs'].ctypes.data, nat['k'], mask.ctypes.data, on.ctypes.data, len(on) if only is not None else 0, out.ctypes.data, tot)
    return out[:m].tobytes() if m > 0 else b''


FRAME = os.environ.get('RVT_Q_FRAME', '1') == '1'             # Python 102 framing when the C helper is unavailable
PAD8 = bytes(8)


def _resync102(chunk, lo, hi, n, nt, W=8):
    """first record prefix position p in [lo, hi) of a 102 chunk region whose length chain verifies STRONGLY (at least one checked hop: the next
    prefix equals this record's length; ids in the id table, tags in the schema; up to 6 hops). A candidate whose first record runs past the chunk end
    cannot be checked: a real one would be the last record start of the chunk, so it is never preferred over a strong one and alone it gives None
    (the caller falls back to the old scan). Layout from the record start p: [u32 prev length][id: W bytes][u32][u32 L][u16 tag]. -> (p or None, weak seen)"""
    import numpy as np
    ro = 4 + W + 4; m = min(hi, n - 24)
    if m <= lo: return None, False
    bb = np.frombuffer(chunk, np.uint8)
    P = np.arange(lo, m)
    def u32(Q): return bb[Q].astype(np.uint64) | bb[Q + 1].astype(np.uint64) << 8 | bb[Q + 2].astype(np.uint64) << 16 | bb[Q + 3].astype(np.uint64) << 24
    L = u32(P + ro); T = bb[P + ro + 4].astype(np.int64) | bb[P + ro + 5].astype(np.int64) << 8
    ok = (T >= 12) & (T < nt)
    E = P.astype(np.uint64) + ro + 4 + L
    inside = E + 4 <= n
    weak = bool((ok & ~inside).any())
    ii = np.flatnonzero(ok & inside)
    if not len(ii): return None, weak
    sel = u32(E[ii].astype(np.int64)) == L[ii]
    for p in P[ii[sel]].tolist():
        if _chain_ok(chunk, p, n, nt, 6, W): return p, weak
    return None, weak


def _id_known(e):
    import numpy as np
    ids = _G['ids']; k = int(np.searchsorted(ids, np.uint64(e))); return k < len(ids) and int(ids[k]) == e


def _id_top():
    t = _G.get('id_top')
    if t is None: t = _G['id_top'] = 2 * int(_G['ids'][-1]) + (1 << 20) if len(_G['ids']) else 1 << 40
    return t


def _rid(chunk, p, W):
    return struct.unpack_from('<Q' if W == 8 else '<I', chunk, p)[0]


def _chain_ok(chunk, p, n, nt, hops, W=8):
    """True when the length chain from p verifies at least 2 hops (next prefix == length; plausible id: below twice the largest table id; tag in the
    schema), or ends exactly at a run trailer"""
    uf = struct.unpack_from; top = _id_top(); good = 0; ro = 4 + W + 4
    for h in range(hops):
        if p + ro + 6 > n: return good >= 2
        e = _rid(chunk, p + 4, W); L, = uf('<I', chunk, p + ro); t, = uf('<H', chunk, p + ro + 4)
        if not (12 <= t < nt) or e >= top: return False
        E = p + ro + 4 + L
        if E + 4 > n: return good >= 2
        if uf('<I', chunk, E)[0] != L: return False
        good += 1; p = E
    return True


def frame_records(chunk, sizes, segs, nmain, W=8):
    """[(id pos, record end, id, tag)] of every 102 record whose id lies in the task's main segments, by the length framing of channel 102:
    [u32 length of the previous record][id: W bytes][u32][u32 L][u16 tag ... L bytes]; a run starts without the previous-length word (inflate_run's 8-byte pad
    stands in for it). The task's first segment may start mid-run: resync. Every hop is checked (next prefix == L); any mismatch -> None (old scan)."""
    n = len(chunk); nt = 12 + len(_G['cls']); uf = struct.unpack_from; top = _id_top(); ro = 4 + W + 4; none = (1 << (8 * W)) - 1; tsz = 4 + W + 12
    bounds = [0]
    for z in sizes: bounds.append(bounds[-1] + z)
    if len(bounds) != len(segs) + 1 or bounds[-1] != n: return None
    main_end = bounds[nmain]
    rs = [0] + [i for i in range(1, len(segs)) if segs[i][0] != segs[i - 1][0] + segs[i - 1][1] + 24]
    out = []
    for k, i in enumerate(rs):
        if bounds[i] + 8 >= main_end: break
        run_end = bounds[rs[k + 1]] if k + 1 < len(rs) else n
        if i == 0:
            # the task may start mid-run: first verified record start, segment by segment through the main part (blob continuations hold none)
            p = None; j = 0
            while p is None and j < nmain and (j == 0 or j not in rs):
                p, weak = _resync102(chunk, max(4, bounds[j]), bounds[j + 1], n, nt, W)
                if p is None and weak: _G['why'] = 'weak'; return None
                j += 1
            if p is None: continue                  # no record starts before the next run (one big record from an earlier task)
        else: p = bounds[i] + 4
        while p + 4 < main_end:
            if p + ro + 6 > run_end:
                if run_end < n and p + 4 == run_end: break          # clean end of a complete run (4-byte trailer)
                if run_end == n: break
                _G['why'] = 'runend %d %d' % (p, run_end); return None
            e = _rid(chunk, p + 4, W); L, = uf('<I', chunk, p + ro); t, = uf('<H', chunk, p + ro + 4)
            if e == none and p + tsz == run_end and L == 0: break          # run terminator: [prefix][id -1][1][0][0], ends exactly at the run end
            if not (12 <= t < nt) or (e >= top and e != none): _G['why'] = 'tag/id p=%d run_end=%d n=%d main_end=%d e=%x t=%d L=%d %s' % (p, run_end, n, main_end, e, t, L, chunk[p:p+32].hex()); return None
            E = p + ro + 4 + L
            out.append((p + 4, min(E, n), e, t))
            if E + 4 <= run_end:
                if uf('<I', chunk, E)[0] != L: _G['why'] = 'chain'; return None
            elif run_end < n: _G['why'] = 'past-run-end'; return None
            p = E
    return out


FI_REDUCED = ('CategoryElem', 'FamilySurrogate', 'FamSymSurrogate', 'GStyleElem')


def _plain(v, depth=0):
    """EID -> int, numbers/strings kept, short numeric vectors kept, pointers to an object with a name -> that name; everything else dropped (None)"""
    if type(v).__name__ == 'EID':                 # an int subclass: check it first (ids are unsigned on disk, -1 = none)
        x = int(v)
        if x >= 1 << 63: return x - (1 << 64)
        if 0xFF000000 <= x < 1 << 32: return x - (1 << 32)        # 4-byte-id files (2019 and older): -1 and built-in parameter ids as unsigned 32-bit
        return x
    if v is None or isinstance(v, (bool, int, float, str)): return v
    if isinstance(v, (list, tuple)):
        if len(v) <= 16 and all(isinstance(x, (int, float)) or type(x).__name__ == 'EID' for x in v): return [_plain(x) for x in v]
        if depth == 0 and len(v) <= 64 and all(isinstance(x, (list, tuple)) and len(x) <= 4 for x in v): return [_plain(x, 1) for x in v]
        return None
    if isinstance(v, dict) and depth < 2:
        o = v.get('obj', v)
        if isinstance(o, dict) and isinstance(o.get('m_name'), str) and len(o) <= 3: return o['m_name']
    return None


def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o


def _params(v):
    """{parameter id: value} of a ParamValueSet pointer (instance/type parameter values stored on the element)"""
    o = _ob(v); out = {}
    if isinstance(o, dict):
        for e in o.get('m_paramSet') or []:
            if isinstance(e, dict) and 'm_paramId' in e:
                k = _plain(e['m_paramId']); x = _plain(e.get('m_value'))
                if isinstance(k, int) and x is not None: out[k] = x
    return out


def asset_colors(asset, path='', depth=0, out=None):
    """[(property path, [r, g, b, a])] of every 4-float property of an appearance asset tree, connected assets (textures, tints) included"""
    out = [] if out is None else out
    if not isinstance(asset, dict) or depth > 6: return out
    for pr in asset.get('m_aAProperties') or []:
        x = _ob(pr)
        if not isinstance(x, dict): continue
        nm = '%s/%s' % (path, x.get('m_sName')); v = x.get('m_value')
        if isinstance(v, list) and len(v) == 4 and all(isinstance(t, float) for t in v): out.append((nm, v))
        for k in ('m_aConnected', 'm_aChild'):
            for sub in (x.get(k) or []) if isinstance(x.get(k), list) else []:
                asset_colors(_ob(sub), nm, depth + 1, out)
    return out


def _rgb(v):
    """Revit stores colours as an int 0x00BBGGRR"""
    return None if not isinstance(v, int) or v < 0 else (v & 255, (v >> 8) & 255, (v >> 16) & 255)


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
    pr = {}
    for k in ('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetElementId', 'm_pParamValueSetAString'):
        if f.get(k) is not None: pr.update(_params(f[k]))
    if pr: out['params'] = pr
    sf = _ob(f.get('m_pSurface'))
    if c == 'Level' and isinstance(sf, dict) and isinstance(sf.get('m_origin'), (list, tuple)) and len(sf['m_origin']) == 3: out['elevation'] = float(sf['m_origin'][2])
    cs = _ob(f.get('m_pCompoundStructure'))
    if isinstance(cs, dict) and isinstance(cs.get('m_layers'), list):
        out['layers'] = [(_plain(L.get('m_layerWidth')), _plain(L.get('m_layerFunction')), _plain(L.get('m_materialId'))) for L in cs['m_layers'] if isinstance(L, dict)]
    m = _ob(f.get('m_pMaterial'))
    if isinstance(m, dict):
        out['name'] = m.get('m_name') if isinstance(m.get('m_name'), str) else out.get('name')
        out['material'] = {k: _rgb(m.get(k)) for k in ('m_color', 'm_cutPatternColor', 'm_cutBackgroundPatternColor', 'm_surfacePatternColor', 'm_surfaceBackgroundPatternColor') if k in m}
        out['appearance_asset_id'] = _plain(m.get('m_appearanceAssetId'))
        out['owned_asset_colors'] = [x for oa in (m.get('m_assetMap') or {}).get('m_ownedAssets') or [] for x in asset_colors(_ob(oa), 'owned')]
    a = _ob(f.get('m_pAppearanceAsset'))
    if isinstance(a, dict):
        if isinstance(a.get('m_Name'), str): out['name'] = a['m_Name']
        out['asset_color'] = _rgb(a.get('m_color')); out['asset_colors'] = asset_colors(a.get('m_Asset') if isinstance(a.get('m_Asset'), dict) else None, 'app')
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


def _owner_map(ids, vals):
    """ElemTable column at +28 (+24 for 4-byte ids) per id: fastinfo calls it the owner and skips such Level/Grid/sheet records as group copies. Measured on the
    984 MB file: the 20 sheets it drops point at DBViewDrafting, VarSketch, DBDrawing, Viewer, DBViewPlan, ExtrusionElem and one ElementGroupType, so it is
    not group ownership in general; sheets(rule='last') skips only ids whose value is a group / group type"""
    import numpy as np
    o = np.argsort(ids, kind='stable'); _G['own_ids'] = ids[o]; _G['own_vals'] = vals[o]


def owner_of(e):
    import numpy as np
    a = _G.get('own_ids')
    if a is None or not len(a): return None
    k = int(np.searchsorted(a, np.uint64(e))); return int(_G['own_vals'][k]) if k < len(a) and int(a[k]) == e else None


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
        sel = ow != 0xffffffff; _owner_map(a[sel], ow[sel].astype(np.uint64))
        return uniq(a), uniq(a[ow != 0xffffffff])
    n = (len(et) - 6) // 40
    if 0 < nh <= n: n = nh
    r = np.frombuffer(et, np.uint8, count=n * 40, offset=6).reshape(n, 40)
    a = r[:, :8].copy().view('<u8').ravel(); b = r[:, 20:28].copy().view('<u8').ravel(); ow = r[:, 28:36].copy().view('<u8').ravel()
    top = int(a.max()) + 16
    sel = ow != 0xffffffffffffffff; _owner_map(a[sel], ow[sel])
    return uniq(np.concatenate([a, b[(b > 0) & (b < top)]])), uniq(a[ow != 0xffffffffffffffff])


def _setup(path, log):
    from . import rvtfile as FI
    FI._tune(); FI._paths()
    import olefile, rvt_scan as S, rvt_decode as D, fmt_parser as fp, rvtfmt, rvt_fast as F
    from . import elemindex as EI
    t0 = time.time(); _G['st0'] = None
    if _G.get('fd') is not None:
        try: os.close(_G['fd'])
        except OSError: pass
        _G['fd'] = None
    fd = os.open(path, os.O_RDONLY); st0 = _stamp(os.fstat(fd))           # read-only, the only handle: olefile and every forked worker read through it
    _G.update(path=path, fd=fd, st0=st0)                                     # set first: an error while parsing a file that is being saved is reported as a change
    o = olefile.OleFileIO(os.fdopen(os.dup(fd), 'rb')); names = ['/'.join(e) for e in o.listdir(streams=True)]
    pns = sorted(n for n in names if n.startswith('Partitions/'))
    streams = {pn: Stream(o, pn) for pn in pns}; _G.pop('views', None); _G.pop('groups', None)
    cls, _ = fp.parse(rvtfmt.inflate_stream(o.openstream('Formats/Latest').read())[1])
    W = S.id_size(cls); sch = D.Schema(cls)
    import numpy as np
    et = rvtfmt.inflate_stream(o.openstream('Global/ElemTable').read())[1]; ids, owned = _ids_owned(et, W); del et
    try: es = F.es_load(path)[0]
    except Exception: es = {}
    # the geometry STOP list is given explicitly: rvt_decode derives it from RVT_GEOM at import time and rvt_fast sets RVT_GEOM=1 on import, so a child
    # process of an earlier query inherited a different decoder (2024 HVAC sample: 7 vs 53 sub/user category names, other category counts)
    rd = F._rc().RecDecoder(sch.c, W, ['GeomStepList', 'GeomTable'], D.STRCAP, D.EID, D.Desync)
    if es: rd.set_es(es)
    rd.set_ids(ids.tolist())
    # second decoder WITHOUT the geometry STOP list: the stop at GeomStepList/GeomTable also drops what follows it, e.g. SymbolInfo.m_name (type names): 0 of 199
    # type names on the 2024 HVAC sample with STOP, 199 of 199 without; Level elevations.
    # Used only for those record classes (FULL_DECODE; fields would be slower for instances).
    rd_full = F._rc().RecDecoder(sch.c, W, [], D.STRCAP, D.EID, D.Desync)
    if es: rd_full.set_es(es)
    rd_full.set_ids(ids.tolist())
    cnames = {i + 12: c['name'] for i, c in enumerate(cls)}
    log('schema + decoder: %.2fs' % (time.time() - t0))
    _G['gen'] = _G.get('gen', 0) + 1
    _G.update(path=path, fd=fd, st0=st0, damaged=0, o=o, pns=pns, streams=streams, cls=cls, W=W, sch=sch, rd=rd, rd_full=rd_full, ids=ids, owned=owned,
              cnames=cnames, EH=sch.by.get('ElementHeader', -999) + 12)
    consistent()
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
        s.log = log; s.workers = workers; s.pool = None; s.stat = []; s.loc = {}; s.hdr = None; s.plan_kw = {}      # hdr = 'all': every task also decodes every ElementHeader (scan)
        if workers > 1:
            import multiprocessing as mp
            s.pool = mp.get_context('fork').Pool(workers, initializer=_winit)
        else: _winit()
    def close(s):
        """stop the workers, then check the file did not change while it was read (FileChanged replaces any error a torn read caused)"""
        if s.pool:
            t = time.time(); s.pool.terminate(); s.log('pool terminate %.2fs' % (time.time() - t)); s.pool = None
        consistent()
        if _G.get('damaged'): s.log('WARNING: %d gzip segments fail their CRC (file damaged?)' % _G['damaged'])
    def walk_and_decode(s, wanted, note_eh):
        """-> (segtab {pn: segs}, tasks {key: task}, results {key: (recs, ehs, ehc)})"""
        t0 = time.time(); pns = _G['pns']; order = sorted(range(len(pns)), key=lambda i: -_G['streams'][pns[i]].size)
        segtab = {}; tasks = {}; res = {}
        if s.pool is None:
            for pi in order:
                pn = pns[pi]; segtab[pn] = _job(('walk', pi, pn))[1]
                for t in plan(pi, pn, segtab[pn], **s.plan_kw):
                    tasks[t[0]] = t; b = _job(('dec',) + t + (wanted, note_eh, s.hdr))[1]; res[t[0]] = b[:3]; _G['damaged'] = _G.get('damaged', 0) + b[3][3]; s.loc[t[0]] = b[4] if len(b) > 4 else None
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
            for t in plan(pi0, pn0, segs, final_only=True, **s.plan_kw):        # a task whose main part and overlap are full cannot change any more
                if t[0] in sent: continue
                sent.add(t[0]); tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, s.hdr),), callback=put, error_callback=err); pending += 1
        fd = os.open(_G['path'], os.O_RDONLY)
        try: segtab[pn0] = _G['streams'][pn0].segments(fd, every=512, cb=early)
        finally: os.close(fd)
        for t in plan(pi0, pn0, segtab[pn0], **s.plan_kw):
            if t[0] in sent:
                assert tasks[t[0]] == t, 'early task differs from plan()'
                continue
            tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, s.hdr),), callback=put, error_callback=err); pending += 1
        if len(segtab) == len(pns): tw = time.time() - t0
        else: tw = None
        while pending:
            r = q.get(); pending -= 1
            if r[0] == 'error': raise r[1]
            head, body = r
            if head[0] == 'walk':
                pi, pn = head[1], head[2]; segtab[pn] = body
                for t in plan(pi, pn, body, **s.plan_kw):
                    tasks[t[0]] = t; s.pool.apply_async(_job, (('dec',) + t + (wanted, note_eh, s.hdr),), callback=put, error_callback=err); pending += 1
                if len(segtab) == len(pns): tw = time.time() - t0
            else:
                res[head[1]] = body[:3]; s.stat.append(body[3]); _G['damaged'] = _G.get('damaged', 0) + body[3][3]; s.loc[head[1]] = body[4] if len(body) > 4 else None
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
            for x in st: busy[x[2]] += x[1]
            s.log('  task cpu %.1fs, task wall %.1fs (max %.2fs), worker busy max %.2fs min %.2fs' % (sum(x[0] for x in st), sum(x[1] for x in st), max(x[1] for x in st), max(busy.values()), min(busy.values())))
        s.log('%s: %d tasks, %d workers, %.2fs%s' % (what, n, s.workers, time.time() - t0, (', ' + extra) if extra else ''))


HDR_MAXWIN = int(os.environ.get("RVT_Q_HDR_MAXWIN", "4"))      # experiment: do not merge header windows longer than this many segments (0 = always merge, the old behaviour; default 4: doors on 6 samples 20-70 MB 0.1-0.17 s faster, 200 runs identical)


def header_jobs(segtab, tasks, res, want_ids, per_task=False):
    """header jobs for `want_ids`: only segments that hold an ElementHeader candidate of a wanted id (noted in the record pass), each window from that
    segment through OVL decoded bytes of the same channel (the same tail a task has), windows of one task merged; asked for just those ids"""
    import numpy as np
    nd = np.array(sorted(int(i) for i in want_ids), np.uint64); jobs = []; gcache = {}
    for key in sorted(res):
        ehc = res[key][2]
        if ehc is None or not len(ehc[0]): continue
        sel = np.isin(ehc[0], nd)
        if not sel.any(): continue
        _, pn, tsegs, nmain = tasks[key]; pi, k0 = key; segs = segtab[pn]
        if pn not in gcache:
            gl = {}
            for idx in _chan_groups(segs):
                for p_, g_ in enumerate(idx): gl[g_] = (idx, p_)
            gcache[pn] = gl
        idx, p0 = gcache[pn][k0]               # the task's channel group and the position of its first segment in it
        # each window asks only for the ids whose candidate opened it: asking every window of a task for all of the task's hit ids let a window
        # opened for another id decode a false header of this id first (first-wins): 1 type lost its category on a 984 MB save
        by_start = collections.defaultdict(set)
        for e_, st_ in zip(ehc[0][sel].tolist(), (p0 + ehc[1][sel]).tolist()): by_start[st_].add(e_)
        win = []
        for st0 in sorted(by_start):
            st = max(0, st0 - 1)               # from the previous segment: a record's bytes before its id may sit there
            m = st; ov = 0
            while m < len(idx) and (m <= st + 1 or ov < OVL): ov += segs[idx[m]][2]; m += 1
            if win and st <= win[-1][1] and (HDR_MAXWIN <= 0 or m - win[-1][0] <= HDR_MAXWIN): win[-1][1] = max(win[-1][1], m); win[-1][2] |= by_start[st0]
            else: win.append([st, m, set(by_start[st0])])
        if per_task:                           # round 2 (old rule): every window of the task asks for all of the task's hit ids
            allh = sorted(set(ehc[0][sel].tolist())); win = [[a, b, allh] for a, b, _ in win]
        for a, b, ids_ in win: jobs.append(((pi, idx[a]), pn, [segs[x] for x in idx[a:b]], b - a, [], False, sorted(ids_)))
    return jobs


def headers(E, segtab, tasks, res, want_ids):
    """{eid: header tuple}, first-wins in stream order. Round 1: each window asks only for the ids whose candidate opened it (precise). Round 2, only for
    ids round 1 did not find: every window of their tasks asks for them (the old rule; one railing header on two 984 MB saves is found only this way)."""
    hdr = {}
    for key, (_, ehs, _) in sorted(E.run(header_jobs(segtab, tasks, res, want_ids), 'headers').items()):
        for e, h in ehs:
            if e not in hdr: hdr[e] = h
    miss = [e for e in want_ids if e not in hdr]
    if miss:
        for key, (_, ehs, _) in sorted(E.run(header_jobs(segtab, tasks, res, miss, per_task=True), 'headers (round 2)').items()):
            for e, h in ehs:
                if e not in hdr: hdr[e] = h
    return hdr


def classes(path, want, header_ids=None, workers=None, log=None, last_wins=False):
    """generic primitive: first-wins reduced records of the classes `want` (names, or a predicate on the class name) and, optionally, the ElementHeaders
    (cat, owner view, family, classdef) of `header_ids` (callable: ids from the records). -> (records {(eid, class): rec}, headers {eid: tuple}, G)"""
    log = log or (lambda *a: None); workers = workers or _workers()
    G = _setup(path, log); pred = want if callable(want) else (lambda c, w=set(want): c in w)
    wanted = sorted(t for t, n in G['cnames'].items() if pred(n))
    log('  @%.3f setup done' % (time.time() - _T0))
    E = Engine(workers, log)
    log('  @%.3f pool up' % (time.time() - _T0))
    try:
        segtab, tasks, res = E.walk_and_decode(wanted, header_ids is not None)
        log('  @%.3f records done' % (time.time() - _T0))
        recs = {}
        for key in sorted(res):
            for k, v in res[key][0]:
                if last_wins or k not in recs: recs[k] = v          # last_wins: across tasks (inside one task the decoder keeps the first)
        hdr = {}
        hid = header_ids(recs) if callable(header_ids) else header_ids
        if hid:
            hdr = headers(E, segtab, tasks, res, list(hid))
    finally: E.close()
    return recs, hdr, G


def _group_classes():
    if 'groups' not in _G: _G['groups'] = subclasses(_G['cls'], 'ElementGroupType') | subclasses(_G['cls'], 'ElementGroup')
    return _G['groups']


def _view_classes():
    if 'views' not in _G: _G['views'] = subclasses(_G['cls'], 'DBView')
    return _G['views']


def _workers():
    """RVT_Q_WORKERS, else from a memory budget RVT_Q_MEM_GB (default 3) in PSS terms: measured on the 984 MB file ~250 MB master + ~70 MB per forked worker
    (4 workers 478 MB PSS 3.5 s, 8 workers 758 MB 2.3 s, 20 workers 1363 MB 2.0 s); capped at 20 (no gain beyond on a 28-thread box) and cpus - 1.
    For the 900 MB suite cap use RVT_Q_MEM_GB=0.9 (8 workers)."""
    n = int(os.environ.get('RVT_Q_WORKERS', '0') or 0)
    if n: return n
    budget = float(os.environ.get('RVT_Q_MEM_GB', '3')) * 1024
    return max(1, min((os.cpu_count() or 2) - 1, 20, int((budget - 250) // 70)))


def sheets(path, workers=None, log=None):
    """sheets (number, name, issue date, drawn/approved by, revisions, views), the same list scan() gives, decoding only views, viewports, revisions and groups.
    Rule: the last record in stream order wins for a sheet id with several records, and a sheet is skipped only when its ElemTable column +28 points at a
    group / group type. 984 MB project file: 412 listed, 412 equal Revit's export by number and title, 0 extra (the old first-wins reader that skipped every id
    with a +28 value: 393 listed, 391 equal). Same list as the old reader on every Autodesk sample 2017-2026."""
    log = log or (lambda *a: None); workers = workers or _workers(); t0 = time.time()
    # only real views (subclasses of DBView: sheets are DBViewDrafting), their Viewports and the revisions. fastinfo decodes every DBView* class: DBViewInfo,
    # DBViewType, the cutters are not views, and false DBViewInfo candidates (ids < 1000 inside bulk data) cost 128 of 170 CPU seconds on a 984 MB file
    # DBView* prefix as well: fastinfo names views of the DBView* classes only (TableView / PanelScheduleView on a sheet are not listed there either; kept equal)
    def want(c, keep=[]):
        return c.startswith('DBView') and c in _view_classes() or c in ('Viewport', 'ProjectRevision') or c in _group_classes()
    def need_headers(full):
        # 2023+ files: a sheet lists no viewports; each Viewport is owned by its sheet (ElementHeader.m_ownerViewId)
        sheet_lists = [r['fields'].get('m_sheetViewportElemIds') for (e, c), r in full.items() if c == 'DBViewDrafting' and r['fields'].get('m_sheetNumber') and r['fields'].get('m_viewName') is not None]
        vps = [e for (e, c) in full if c == 'Viewport']
        return vps if vps and any(not x for x in sheet_lists) else []
    full, hdr, G = classes(path, want, need_headers, workers, log, last_wins=True)
    import numpy as np
    recs = {}; by = collections.defaultdict(list)
    groups = {e for (e, c) in full if c in _group_classes()}
    for (eid, c), r in full.items():
        if c == 'DBViewDrafting' and owner_of(eid) in groups: continue        # a copy inside a group type (2024 HVAC sample: 'Unnamed' sheet)
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
        from . import rvtfile as FI
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
    'RoofBase': ('RoofBase',), 'Roof': ('RoofBase',), 'RoofType': ('RoofAttributesBase',), 'Stairs': ('StairsElement',), 'StairsType': ('StairsSym',),
    'Area': ('RoomElem',), 'Space': ('RoomElem',), 'AnnotationSymbol': ('FamilyInstance',),
    'Railing': ('BaseRailing', 'Railing'), 'RailingType': ('BaseRailingSym', 'BaseRailingAttr'), 'FamilyInstance': ('FamilyInstance',),
    'FamilySymbol': ('FamilySymbol',), 'ElementType': ('Symbol',), 'Family': ('Family',), 'Material': ('MaterialElem',), 'Room': ('RoomElem',),
    'TextNote': ('TextNote',), 'Dimension': ('Dimension',), 'IndependentTag': ('IndependentTag', 'TagElem'), 'RevitLinkInstance': ('LinkInstance',),
    'Revision': ('ProjectRevision',), 'Viewport': ('Viewport',), 'Phase': ('ProjectPhase',), 'Group': ('ElementGroup',), 'GroupType': ('ElementGroupType',),
    'CurtainGridLine': ('CurtainWallGridLine',), 'Mullion': ('FamilyInstance',), 'Panel': ('FamilyInstance',),
}
# Revit API classes that the file stores as one schema class split by category (measured on the gt4 Revit dumps of 9 samples 2020-2026: AnnotationSymbol
# = FamilyInstance in Generic Annotations, Mullion / Panel = FamilyInstance in Curtain Wall Mullions / Curtain Panels; Room / Area / Space = RoomElem in Rooms / Areas / Spaces)
ALIAS_CATS = {'FamilyInstance': ('not', {-2000150, -2000170, -2000171}), 'AnnotationSymbol': ('in', {-2000150}), 'Mullion': ('in', {-2000171}), 'Panel': ('in', {-2000170}), 'Room': ('in', {-2000160}), 'Area': ('in', {-2003200}), 'Space': ('in', {-2003600})}
# categories answered without a class: candidate classes (the ElementHeader category then filters exactly). Loadable-family categories -> FamilyInstance.
CATEGORY_CLASSES = {
    'Walls': ('ArcWall', 'SWall', 'FaceWall'), 'Floors': ('Floor',), 'Ceilings': ('Ceiling',), 'Roofs': ('RoofBase',), 'Stairs': ('StairsElement', 'Stairs', 'MultistoryStairs'),
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


def _builtin_param(params, name):
    """value of the built-in parameter called `name` (reader PNAMES table, same names the editor accepts) stored on this element, else None; ids of one name are tried in table order (c4x-rvtdiff 167/168: --fields Mark printed blank for a ParamValueAString mark)"""
    if not params or not isinstance(name, str): return None
    try:
        import sys, os
        rr = os.path.expanduser('~/rvt-research')
        if rr not in sys.path: sys.path.insert(0, rr)
        import rvt_params
    except ImportError: return None
    for k, v in rvt_params.PNAMES.items():
        if v == name and int(k) in params: return params[int(k)]
    return None


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
    acat = ALIAS_CATS.get(cls if isinstance(cls, str) else (cls[0] if cls and len(cls) == 1 else None))
    tag_of = {n: t for t, n in G['cnames'].items()}
    aux = {'Level', 'CategoryElem', 'FamilySurrogate', 'FamSymSurrogate'}
    sym = subclasses(G['cls'], 'Symbol') | {'Level'}           # no-STOP decoder: type names (SymbolInfo) and Level elevations (m_pSurface.m_origin) sit behind the geometry stop
    spec = [{'tags': sorted(tag_of[n] for n in (want | aux) - sym if n in tag_of), 'mode': 'lite'}]
    spec = [x for x in spec if x['tags']]
    fl = (want | aux) & sym
    if fl: spec.append({'tags': sorted(tag_of[n] for n in fl if n in tag_of), 'mode': 'lite', 'full': True})
    stags = sorted(tag_of[n] for n in sym - {'Level'} if n in tag_of)
    if names and stags and LOCATE: spec.append({'tags': stags, 'locate': True})
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
            hdr = headers(E, segtab, tasks, res, list(rows))
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
            import numpy as np
            nd = np.asarray(need, np.uint64)
            def has(k):     # the record locator of pass 1 (102 tasks framed natively): only tasks that hold a needed type record; unknown -> asked
                lc = E.loc.get(k)
                if lc is None:
                    t_ = tasks[k]; return not (SPLIT and len(t_[2][0]) > 3 and t_[2][0][3] == 101)       # 101 tasks decode no records under SPLIT
                return bool(np.isin(lc, nd).any())
            # only the occurrence that wins can matter (rule last: the last task holding the id, first: the first); tasks without a locator get every id.
            # ids that come back without a decoded record are asked again of every task holding them (round 2 = the old rule for those ids)
            ks = sorted(tasks); assign = collections.defaultdict(set); unknown = []
            for k in ks:
                lc = E.loc.get(k)
                if lc is None:
                    if has(k): unknown.append(k)
                    continue
                for e in lc[np.isin(lc, nd)].tolist(): assign[e].add(k)
            per = collections.defaultdict(set)
            for e in need:
                if e in assign: per[max(assign[e]) if rule == 'last' else min(assign[e])].add(e)
            for k in unknown: per[k] |= set(need)
            def tjobs(per_):
                return [tasks[k] + ([{'tags': stags, 'mode': 'lite', 'full': True, 'only': sorted(per_[k])}], False, None) for k in sorted(per_)]
            got = collections.defaultdict(list)
            for key, (rr, _, _) in E.run(tjobs(per), 'types by id').items():
                for (e, c), r in rr: got[key].append((e, c, r))
            miss = set(need) - {e for v in got.values() for e, _, _ in v}
            if miss:
                per2 = collections.defaultdict(set)
                for e in miss:
                    for k in assign.get(e, ()): per2[k].add(e)
                for k in unknown: per2[k] |= miss
                for key, (rr, _, _) in E.run(tjobs(per2), 'types by id (round 2)').items():
                    for (e, c), r in rr:
                        if e in miss: got[key].append((e, c, r))
            for key in sorted(got):
                for e, c, r in got[key]:
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
        cid_ = cb if cb is not None else craw
        if acat and (acat[0] == 'in' and cid_ not in acat[1] or acat[0] == 'not' and cid_ in acat[1]): continue
        t = tid.get(e); tr = types.get(t)
        lv = f.get('m_assocLevelId'); lv = lv if isinstance(lv, int) and lv > 0 else None
        row = {'id': e, 'class': c, 'name': f.get('name'), 'type_id': t, 'type_name': tr[1]['fields'].get('name') if tr else None,
               'level_id': lv, 'level': levels.get(lv), 'category_id': cb if cb is not None else craw, 'category': ct.get(cb) if cb is not None else None,
               'owner_view_id': _sid(h[1], W) if h else None}
        if row['owner_view_id'] in (-1, 0): row['owner_view_id'] = None
        if row['name'] is None and row['type_name']: row['name'] = row['type_name']           # Revit: Element.Name of an instance is its type name
        for k in (fields or ()):
            if k not in row:
                row[k] = f.get(k)
                if row[k] is None: row[k] = _builtin_param(f.get('params'), k)      # c4x-rvtdiff 167: --fields Mark printed blank for a Mark stored as ParamValueAString (house3 window 301610 'W1.0.1')
        if where and any(str(row.get(k)) != str(v) for k, v in where.items()): continue
        out.append(row)
    log('collect: %d rows, %.2fs' % (len(out), time.time() - t0))
    return out


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# benchmark: walls below a height whose type layers use a material with a red colour in any colour property

WALL_USER_HEIGHT = -1001105        # BuiltInParameter.WALL_USER_HEIGHT_PARAM (Unconnected Height; stored on every wall, but stale when the top is constrained)
WALL_BASE_LEVEL, WALL_BASE_OFFSET, WALL_TOP_LEVEL, WALL_TOP_OFFSET, WALL_TOP_ATTACHED = -1001107, -1001108, -1001103, -1001109, -1001117


def wall_height(f, elev):
    """(height ft, how): Revit's Unconnected Height. Top constrained to a level: top elevation + Top Offset - (base elevation + Base Offset) (the stored value is
    stale then: equal to Revit for only 170 of 775 walls on 9 samples); unconnected: the stored value. how = 'levels' | 'stored' | None; walls whose top is attached
    to a roof/floor are marked 'attached' (Revit trims them; not reproduced)"""
    pr = f.get('params') or {}
    base = pr.get(WALL_BASE_LEVEL, f.get('m_assocLevelId')); top = pr.get(WALL_TOP_LEVEL, f.get('m_upToLevelId'))
    bo = pr.get(WALL_BASE_OFFSET, 0.0) or 0.0; to = pr.get(WALL_TOP_OFFSET, 0.0) or 0.0
    how = 'attached' if pr.get(WALL_TOP_ATTACHED) else None
    if isinstance(top, int) and top > 0 and top in elev and isinstance(base, int) and base in elev:
        return elev[top] + to - (elev[base] + bo), how or 'levels'
    h = pr.get(WALL_USER_HEIGHT)
    return (h, how or 'stored') if isinstance(h, (int, float)) else (None, None)
NAMED = {'red': (255, 0, 0), 'dark red': (139, 0, 0), 'brick': (170, 74, 68), 'orange': (255, 165, 0), 'brown': (150, 75, 0), 'pink': (255, 192, 203),
         'yellow': (255, 255, 0), 'green': (0, 128, 0), 'blue': (0, 0, 255), 'purple': (128, 0, 128), 'grey': (128, 128, 128), 'white': (255, 255, 255), 'black': (0, 0, 0)}


def is_red(rgb, hue=15.0, sat=0.4, val=0.25):
    """the benchmark's rule: HSV hue within +-hue degrees of 0, saturation >= sat, value >= val (rgb 0-255 ints or 0-1 floats)"""
    import colorsys
    if rgb is None: return False
    r, g, b = rgb[:3]
    if max(r, g, b) > 1.0 or all(isinstance(x, int) for x in (r, g, b)) and max(r, g, b) > 1: r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s_, v = colorsys.rgb_to_hsv(max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))
    h *= 360.0
    return (h <= hue or h >= 360.0 - hue) and s_ >= sat and v >= val


def nearest_name(rgb):
    if rgb is None: return None
    r, g, b = [x * 255.0 if max(rgb[:3]) <= 1.0 else x for x in rgb[:3]]
    return min(NAMED, key=lambda k: sum((a - c) ** 2 for a, c in zip((r, g, b), NAMED[k])))


def material_colors(mat, assets):
    """[(property, rgb)] of one MaterialElem: graphics colour, cut/surface pattern foreground/background, owned assets, appearance asset (its own colour
    + every 4-float property of its tree)"""
    f = mat['fields']; out = [(k, v) for k, v in (f.get('material') or {}).items() if v is not None]
    out += [(p, v) for p, v in f.get('owned_asset_colors') or []]
    a = assets.get(f.get('appearance_asset_id'))
    if a:
        if a['fields'].get('asset_color') is not None: out.append(('asset m_color', a['fields']['asset_color']))
        out += [(p, v) for p, v in a['fields'].get('asset_colors') or []]
    return out


def walls_red_material(path, max_height_ft=5 / 0.3048, workers=None, log=None, rule='last', pred=None):
    """-> dict(count, walls, ...): walls with Unconnected Height < max_height_ft whose wall type has a compound-structure layer whose material has a red colour
    (is_red) in any colour property. One cold pass: walls (geometry STOP decoder), wall types + materials + appearance assets (no-STOP decoder), joins in memory."""
    log = log or (lambda *a: None); workers = workers or _workers(); t0 = time.time()
    G = _setup(path, log); tag_of = {n: t for t, n in G['cnames'].items()}; t1 = time.time()
    wall_c = _class_set(G['cls'], 'Wall'); type_c = _class_set(G['cls'], 'WallType'); mat_c = {'MaterialElem'}; ast_c = {'AppearanceAssetElem'}
    spec = [{'tags': sorted(tag_of[n] for n in wall_c if n in tag_of), 'mode': 'lite'},
            {'tags': sorted(tag_of[n] for n in type_c | mat_c | ast_c | {'Level'} if n in tag_of), 'mode': 'lite', 'full': True}]
    E = Engine(workers, log)
    try: segtab, tasks, res = E.walk_and_decode(spec, False)
    finally: E.close()
    t2 = time.time(); full = {}
    for key in sorted(res):
        for k, v in res[key][0]:
            if rule == 'last' or k not in full: full[k] = v
    walls = {e: r for (e, c), r in full.items() if c in wall_c}; types = {e: r for (e, c), r in full.items() if c in type_c}
    mats = {e: r for (e, c), r in full.items() if c in mat_c}; assets = {e: r for (e, c), r in full.items() if c in ast_c}
    red = {}
    for e, m in mats.items():
        cols = material_colors(m, assets); hit = [(p, v) for p, v in cols if (pred or is_red)(v)]
        if hit: red[e] = hit
    elev = {e: r['fields']['elevation'] for (e, c), r in full.items() if c == 'Level' and 'elevation' in r['fields']}
    out = []; nh = 0; nt = 0; hows = collections.Counter()
    for e, w in sorted(walls.items()):
        f = w['fields']; h, how = wall_height(f, elev); hows[how] += 1
        if isinstance(h, (int, float)): nh += 1
        t = f.get('m_WallAttributesId'); tr = types.get(t)
        if tr: nt += 1
        if not isinstance(h, (int, float)) or h >= max_height_ft or not tr: continue
        ms = [L[2] for L in tr['fields'].get('layers') or [] if isinstance(L[2], int)]
        if any(m in red for m in ms): out.append({'id': e, 'type_id': t, 'height_ft': h, 'red_materials': sorted({m for m in ms if m in red})})
    st = {'walls': len(walls), 'walls_with_height': nh, 'height_from': dict(hows), 'walls_with_type': nt, 'wall_types': len(types), 'types_with_layers': sum(1 for r in types.values() if r['fields'].get('layers')),
          'materials': len(mats), 'materials_with_colour': sum(1 for m in mats.values() if material_colors(m, assets)), 'appearance_assets': len(assets),
          'assets_with_colour': sum(1 for a in assets.values() if a['fields'].get('asset_colors')), 'red_materials': len(red), 'count': len(out),
          'seconds': {'setup': round(t1 - t0, 2), 'decode_pass': round(t2 - t1, 2), 'join': round(time.time() - t2, 2), 'total': round(time.time() - t0, 2)}}
    log('walls_red_material: %s' % st)
    return dict(st, rows=out, red=red, _types={e: r['fields'].get('layers') for e, r in types.items()}, _colors={e: material_colors(m, assets) for e, m in mats.items()})


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# scan: the model summary (sheets, views, levels, grids, revisions, phases, counts by category / class, per-element header table) in one cold pass.
# Replaced fastinfo.scan (2026-11-14): same result shape, the corrected sheet rule, the parallel engine.

FULL_DECODE = ('Level',)
# CategoryElem stays on the STOP decoder: without the stop it yields more sub/user category names (2024 HVAC sample 53 vs 7) and parents, but per-element
# categories then agree with Revit's API dump less often (5 samples 2020-2023: 87.8 vs 88.1 percent of 94080 elements): Revit reports the subcategory itself
ADMIN = ('FamilySurrogate', 'FamSymSurrogate', 'GStyleElem', 'CategoryElem', 'Level', 'Grid', 'ProjectPhase', 'ProjectInfo', 'Viewport', 'ProjectRevision', 'ViewSheetSet')
NOCAT = -(1 << 62)


def scan(path, log=None, want_elements=False, counts=True, workers=None):
    """-> dict: levels, grids, views, sheets, revisions, phases, subcategory_names, stats and (counts=True) counts (by category), class_counts, view_owned,
    plus arrays (want_elements: per element id, cat, owner_view, family, bbox, cls, cls_names). counts=False skips the ElementHeader pass (sheets/views/levels/grids
    only). Rules: the last record in stream order wins for an id with several records; Level / Grid / sheet records inside a group (type) are skipped."""
    log = log or (lambda *a: None); workers = workers or _workers(); t0 = time.time()
    G = _setup(path, log); W = G['W']; cls = G['cls']
    vw = _view_classes(); gr = _group_classes()
    pred = lambda c: c in ADMIN or (c.startswith('DBView') and c in vw) or c in gr
    tag_of = {n: t for t, n in G['cnames'].items()}
    wanted = [{'tags': sorted(t for t, n in G['cnames'].items() if pred(n) and n not in FULL_DECODE)},
              {'tags': sorted(tag_of[n] for n in FULL_DECODE if n in tag_of), 'full': True}]      # Level elevation, CategoryElem name/parent: behind the geometry stop
    E = Engine(workers, log); E.hdr = 'all' if counts else None
    if counts: E.plan_kw = {'task_mb': float(os.environ.get('RVT_Q_HDR_TASK_MB', '1')), 'ovl': int(os.environ.get('RVT_Q_HDR_OVERLAP_KB', '512')) << 10}
    # a worker holds the decoded ElementHeader trees of one task: 984 MB file, 20 workers: 8 MB tasks 11-13 s / 6.0 GB PSS, 2 MB 7.0 s / 3.5 GB, 1 MB 7.7 s / 2.6 GB (same result)      # every task also decodes its ElementHeaders: they are scattered (984 MB file: in 4 to 14 of the tasks of a big partition, with gaps)
    try:
        segtab, tasks, res = E.walk_and_decode(wanted, not counts)
        full = {}
        for key in sorted(res):
            for k, v in res[key][0]: full[k] = v          # last wins (across tasks; inside one task the decoder keeps the first)
        hdr = {}
        if counts:
            for key in sorted(res):
                for e, h in res[key][1]:
                    if e not in hdr: hdr[e] = h
        else:              # sheets of 2023+ files list no viewports: each Viewport is owned by its sheet (ElementHeader.m_ownerViewId)
            vps = [e for (e, c) in full if c == 'Viewport']
            if vps:
                for key, (_, ehs, _) in sorted(E.run(header_jobs(segtab, tasks, res, vps), 'headers').items()):
                    for e, h in ehs:
                        if e not in hdr: hdr[e] = h
    finally: E.close()
    from . import rvtfile as RF, categories as CT
    import numpy as np
    groups = {e for (e, c) in full if c in gr}
    recs = {}; by = collections.defaultdict(list)
    owned = G['owned']
    def has_owner(e):
        k = int(np.searchsorted(owned, np.uint64(e))); return k < len(owned) and int(owned[k]) == e
    for (eid, c), r in full.items():
        if eid == 0 and not any(v not in (None, '', 0) for v in r['fields'].values()): continue   # an empty id-0 record: a false candidate (a revision, a nameless level on samples)
        if c in ('Level', 'Grid') and has_owner(eid): continue          # copies: a level with an ElemTable +28 value is not in Revit's list (Technical school 2021-23: 1 each)
        if c == 'DBViewDrafting' and owner_of(eid) in groups: continue   # sheets: only copies inside a group type (the +28 rule dropped 20 real sheets on a 984 MB file)
        by[c].append(r); recs.setdefault(eid, r)
    nm = lambda i: (recs[i]['fields'].get('m_text') or recs[i]['fields'].get('m_viewName') or recs[i]['fields'].get('m_name') or '') if i in recs else ''
    def sid(v):
        return RF._sc(v, W) if v is not None and RF._plausible(v, W) else None
    out = {}
    out['levels'] = sorted([{'id': r['id'], 'name': r['fields'].get('m_text', ''), 'elevation_ft': ((_ob(r['fields'].get('m_pSurface')) or {}).get('m_origin') or [None] * 3)[2]} for r in by['Level']],
                           key=lambda l: (l['elevation_ft'] is None, l['elevation_ft'] if l['elevation_ft'] is not None else 0, l['name'], l['id']))
    out['grids'] = sorted(r['fields'].get('m_text', '') for r in by['Grid'])
    views = []; sh = []
    for c, lst in by.items():
        if not c.startswith('DBView'): continue
        for r in lst:
            f = r['fields']; n = f.get('m_viewName')
            if n is None: continue
            if c == 'DBViewDrafting' and f.get('m_sheetNumber'):
                sh.append({'id': r['id'], 'number': f.get('m_sheetNumber'), 'name': n, 'issue_date': f.get('m_issueDate'), 'drawn_by': f.get('m_drawnBy'), 'approved_by': f.get('m_approvedBy'),
                           'revision_ids': [int(v) for v in (f.get('m_explicitlyPresentRevisionIds') or []) if isinstance(v, int) or hasattr(v, '__int__')],
                           'viewports': [int(v) for v in (f.get('m_sheetViewportElemIds') or [])]})
            else: views.append({'id': r['id'], 'name': n, 'class': c, 'template': bool(f.get('m_isTemplate')), 'scale': f.get('m_scale')})
    vp = {r['id']: int(r['fields'].get('m_dbViewId', -1)) for r in by['Viewport']}
    on_sheet = collections.defaultdict(list)
    for v, dv in vp.items():
        h = hdr.get(v); ov = sid(h[1]) if h else None
        if ov not in (None, -1, 0): on_sheet[ov].append(dv)
    for s in sh:
        ids_ = [vp[v] for v in s.pop('viewports') if v in vp]
        s['views'] = [nm(d) for d in ids_ if d in recs] if ids_ else sorted(nm(d) for d in on_sheet.get(s['id'], []) if d in recs)
    out['views'] = sorted(views, key=lambda v: (v['class'], v['name'], v['id'])); out['sheets'] = sorted(sh, key=lambda s: (str(s['number']), s['id']))
    revs = {r['id']: r['fields'] for r in by['ProjectRevision']}
    out['revisions'] = sorted(({'id': i, 'sequence': f.get('m_sequenceNumber'), 'number': f.get('m_numberStr'), 'description': f.get('m_description'), 'date': f.get('m_date'), 'issued_by': f.get('m_issuedBy')} for i, f in revs.items()),
                              key=lambda r: (r['sequence'] is None, r['sequence'] or 0, r['id']))
    for s in out['sheets']: s['revisions'] = [{'number': revs[i].get('m_numberStr'), 'description': revs[i].get('m_description'), 'date': revs[i].get('m_date')} for i in sorted(s.get('revision_ids') or [], key=lambda i: revs.get(i, {}).get('m_sequenceNumber') or 0) if i in revs]
    out['phases'] = [r['fields'].get('m_name') for r in by['ProjectPhase']]
    # saved sheet sets (print/publish sets, ViewSheetSet): members are drawing ids (m_orderedViewSheetList.m_dbDrawingIds) that sheets and views carry as m_dbDrawingId
    drw = {}
    for (eid, c), r in full.items():
        d = r['fields'].get('m_dbDrawingId') if c.startswith('DBView') else None
        if d is not None and eid in recs: drw[int(d)] = (eid, c, r['fields'])
    sets = []
    for r in by['ViewSheetSet']:
        f = r['fields']; ol = _ob(f.get('m_orderedViewSheetList')); mem = [int(x) for x in (ol.get('m_dbDrawingIds') or [])] if isinstance(ol, dict) else []
        shs = []; vws = []; unk = 0
        for d in mem:
            x = drw.get(d)
            if x is None: unk += 1
            elif x[1] == 'DBViewDrafting' and x[2].get('m_sheetNumber'): shs.append(x[2]['m_sheetNumber'])
            else: vws.append(x[2].get('m_viewName') or '')
        sets.append({'id': r['id'], 'name': f.get('m_name'), 'members': len(mem), 'sheets': shs, 'views': vws, 'unresolved': unk})
    out['sheet_sets'] = sorted(sets, key=lambda x: (str(x['name']), x['id']))
    out['subcategory_names'] = CT.subcategory_names(full)
    out['stats'] = {'damaged_members': _G.get('damaged', 0), 'members': sum(len(v) for v in segtab.values()), 'partitions': len(G['pns']), 'tasks': len(tasks),
                    'decoded_mb': round(sum(x[2] for v in segtab.values() for x in v) / 1e6), 'seconds': round(time.time() - t0, 2), 'workers': workers}
    if counts:
        idarr = G['ids']; N = len(idarr); ENDX = len(cls)
        seen = np.zeros(N, bool); a_cat = np.full(N, NOCAT, np.int64); a_ov = np.full(N, -1, np.int64); a_fam = np.full(N, -1, np.int64)
        a_bb = np.full((N, 6), np.nan, np.float32); a_cls = np.full(N, 65535, np.uint16); cn_ix = {}; cnames_l = []
        he = np.array(sorted(hdr), np.uint64); ks = np.searchsorted(idarr, he); ks[ks >= N] = 0; ok = idarr[ks] == he
        for e, k in zip(he[ok].tolist(), ks[ok].tolist()):
            cid, ov, fam, cd, bb = hdr[e]; seen[k] = True
            if isinstance(cd, int) and 12 <= cd < 12 + ENDX:
                n_ = cls[cd - 12]['name']; ci = cn_ix.get(n_)
                if ci is None: ci = cn_ix[n_] = len(cnames_l); cnames_l.append(n_)
                a_cls[k] = ci
            x = sid(cid)
            if x is not None: a_cat[k] = x
            x = sid(ov)
            if x is not None: a_ov[k] = x
            x = sid(fam)
            if x is not None: a_fam[k] = x
            if bb: a_bb[k] = bb
        a_cat = CT.resolve(a_cat, a_cls, np.array(cnames_l or ['']), idarr, full, W)
        cat = _cat_table(); cc = collections.Counter()
        u, n = np.unique(a_cat[seen], return_counts=True)
        for v, c in zip(u.tolist(), n.tolist()):
            if v != NOCAT: cc[cat.get(v, '(built-in id %s, not in the category table)' % v if v < -1 else '(user category id %s)' % v)] += c
        m_ = seen & (a_cat == NOCAT); un, nn = np.unique(a_cls[m_], return_counts=True)
        for i_, c in zip(un.tolist(), nn.tolist()): cc['(no category: %s) %s' % (CT.kind(cnames_l[i_]) if i_ != 65535 else 'other', cnames_l[i_] if i_ != 65535 else '?')] += c
        out['counts'] = dict(cc.most_common())
        u, n = np.unique(a_cls[seen & (a_cls != 65535)], return_counts=True)
        out['class_counts'] = dict(sorted(((cnames_l[int(i)], int(c)) for i, c in zip(u, n)), key=lambda t: -t[1]))
        out['view_owned'] = int(((a_ov != -1) & seen).sum())
        out['stats'].update(elements_with_header=int(seen.sum()), primary_elements=N)
        if want_elements:
            out['arrays'] = {'id': idarr[seen], 'cat': a_cat[seen], 'owner_view': a_ov[seen], 'family': a_fam[seen], 'bbox': a_bb[seen], 'cls': a_cls[seen], 'cls_names': np.array(cnames_l or [''], dtype=str)}
    out['stats']['seconds'] = round(time.time() - t0, 2)
    log('scan: %d sheets, %d views, %d levels, %s headers, %.2fs' % (len(out['sheets']), len(out['views']), len(out['levels']), out['stats'].get('elements_with_header', '-'), time.time() - t0))
    return out


READY = {'walls': {'cls': 'Wall'}, 'wall-types': {'cls': 'WallType'},
         'floors': {'cls': 'Floor'}, 'floor-types': {'cls': 'FloorType'}, 'roofs': {'cls': 'RoofBase'}, 'ceilings': {'cls': 'Ceiling'}, 'stairs': {'cls': 'Stairs'},
         'railings': {'cls': 'Railing'}, 'rooms': {'cls': 'Room'}, 'doors': {'category': 'Doors'}, 'windows': {'category': 'Windows'},
         'furniture': {'category': 'Furniture'}, 'generic-models': {'category': 'Generic Models'}, 'columns': {'category': 'Structural Columns'},
         'framing': {'category': 'Structural Framing'}, 'family-instances': {'cls': 'FamilyInstance'}, 'types': {'cls': 'FamilySymbol'}, 'families': {'cls': 'Family'},
         'materials': {'cls': 'Material'}, 'revisions': {'cls': 'Revision'}, 'schedules': {'cls': 'ViewSchedule'}, 'links': {'cls': 'RevitLinkInstance'},
         'text-notes': {'cls': 'TextNote'}, 'dimensions': {'cls': 'Dimension'}, 'curtain-panels': {'category': 'Curtain Panels'}}


SUMMARY = ('sheets', 'sheet-sets', 'views', 'levels', 'grids', 'counts', 'elements')
HELP = {
    'sheets': 'all sheets: number, title, issue date, revisions, placed views (decodes views/viewports/revisions only)',
    'sheet-sets': 'saved sheet sets (print/publish sets) with their member sheet numbers and views',
    'views': 'all views by class (templates counted, not listed); --json includes templates and scale',
    'levels': 'levels with elevation (ft and m)',
    'grids': 'grid names',
    'counts': 'element counts by category and by class (every ElementHeader is decoded)',
    'elements': 'one row per element: id, class, category, owner view, family, bounding box (ft)',
    'collect': 'general collector: --class (Revit API or schema class) and/or --category, like FilteredElementCollector',
    'walls-red-material': 'benchmark: walls below 5 m whose type has a layer material with a red colour in any colour property',
}
for _k, _v in READY.items(): HELP.setdefault(_k, 'collect ' + ', '.join('%s=%s' % kv for kv in _v.items()))
EPILOG = """examples:
  rvt-ballet sheets FILE.rvt                       (same as: rvt-ballet query sheets FILE.rvt)
  rvt-ballet query walls FILE.rvt --tsv
  rvt-ballet query collect FILE.rvt --class Wall --fields m_assocLevelId --json
  rvt-ballet query collect FILE.rvt --category Doors --where level=Level 1
  rvt-ballet query counts FILE.rvt --json
Every command reads the file cold (no index, no cache), read-only, in about 2-4 s for a 1 GB model with the default memory budget
(RVT_Q_MEM_GB=3, about 20 worker processes; RVT_Q_WORKERS=N to set them). Lengths are Revit internal feet unless a field says otherwise.
If the file changes while it is read (Revit saving it), the query is retried (RVT_Q_RETRIES, default 2) and otherwise fails with
'changed during read: retry' (exit 75): an answer is never built from a torn read. Agent guide: docs/agent-queries.md"""


def _cmd_list():
    w = max(len(k) for k in HELP)
    return '\n'.join('  %-*s  %s' % (w, k, HELP[k]) for k in list(SUMMARY) + ['collect', 'walls-red-material'] + sorted(READY))


def _parser():
    import argparse
    ap = argparse.ArgumentParser(prog='rvt-ballet query', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='cold read-only queries on a .rvt file (no index, no conversion). Commands:\n' + _cmd_list(), epilog=EPILOG)
    ap.add_argument('cmd', metavar='COMMAND', choices=SUMMARY + ('collect', 'walls-red-material') + tuple(sorted(READY))); ap.add_argument('file', metavar='FILE.rvt')
    ap.add_argument('--class', dest='cls', help='collect: Revit API or schema class name(s), comma separated (subclasses included)')
    ap.add_argument('--category', help='collect: built-in category name or id'); ap.add_argument('--fields', default='', help='collect: extra raw fields, comma separated')
    ap.add_argument('--where', action='append', default=[], help='collect: KEY=VALUE equality filter on a row key (repeatable)')
    ap.add_argument('--json', action='store_true', help='JSON output'); ap.add_argument('--tsv', action='store_true', help='tab separated rows with a header line')
    ap.add_argument('--limit', type=int, default=0, help='elements: first N rows only'); ap.add_argument('--verbose', action='store_true', help='timings on stderr')
    ap.add_argument('--workers', type=int, default=0, help='worker processes (default from RVT_Q_MEM_GB)')
    ap.add_argument('--refresh', action='store_true', help=argparse.SUPPRESS)          # accepted for old scripts: there is no cache any more
    return ap


def _fmt_ft(v): return '' if v is None else '%.3f ft (%.3f m)' % (v, v * 0.3048)


def _tsv(cols, rows, say):
    say('\t'.join(cols))
    for r in rows: say('\t'.join('' if r.get(k) is None else (', '.join(map(str, r[k])) if isinstance(r[k], list) else str(r[k])) for k in cols))


def _summary(a, say, log):
    import json
    if a.cmd == 'sheets':
        r = {'sheets': sheets(a.file, workers=a.workers or None, log=log)}
    else: r = scan(a.file, log=log, want_elements=a.cmd == 'elements', counts=a.cmd in ('counts', 'elements'), workers=a.workers or None)
    if _G.get('damaged'): print('rvt-ballet: WARNING: %d compressed blocks of this file fail their checksum: the file looks damaged and the result may be incomplete' % _G['damaged'], file=sys.stderr)
    if a.cmd == 'sheets':
        sh = r['sheets']
        if a.json: say(json.dumps(sh, indent=1, default=str)); return 0
        if a.tsv: _tsv(['id', 'number', 'name', 'issue_date', 'drawn_by', 'approved_by', 'views'], sh, say); return 0
        say('Sheets (%d):' % len(sh))
        for s in sh: say('  %-8s %s%s%s | views: %s' % (s['number'], s['name'], ('  (issued %s)' % s['issue_date']) if s.get('issue_date') else '', ('  rev %s' % '; '.join('%s %s' % (x['number'], x['description']) for x in s['revisions'])) if s.get('revisions') else '', ', '.join(s['views']) or '-'))
    elif a.cmd == 'sheet-sets':
        ss = r['sheet_sets']
        if a.json: say(json.dumps(ss, indent=1, default=str)); return 0
        if a.tsv: _tsv(['id', 'name', 'members', 'sheets', 'views', 'unresolved'], ss, say); return 0
        say('Sheet sets (%d):' % len(ss))
        for x in ss: say('  %s: %d members, sheets: %s%s%s' % (x['name'], x['members'], ', '.join(map(str, x['sheets'])) or '-', ('; views: ' + ', '.join(x['views'])) if x['views'] else '', ('; %d not resolved' % x['unresolved']) if x['unresolved'] else ''))
    elif a.cmd == 'views':
        if a.json: say(json.dumps(r['views'], indent=1, default=str)); return 0
        if a.tsv: _tsv(['id', 'class', 'name', 'template', 'scale'], r['views'], say); return 0
        vv = [v for v in r['views'] if not v['template']]; say('Views (%d, %d templates not listed):' % (len(vv), len(r['views']) - len(vv)))
        for v in vv: say('  %-18s %s' % (v['class'].replace('DBView', ''), v['name']))
    elif a.cmd == 'levels':
        if a.json: say(json.dumps(r['levels'], indent=1, default=str)); return 0
        if a.tsv: _tsv(['id', 'name', 'elevation_ft'], r['levels'], say); return 0
        for l in r['levels']: say('%-30s %s' % (l['name'], _fmt_ft(l['elevation_ft'])))
    elif a.cmd == 'grids':
        if a.json: say(json.dumps(r['grids'], indent=1, default=str)); return 0
        for g in r['grids']: say(g)
    elif a.cmd == 'counts':
        out = {'subcategories': sorted((r.get('subcategory_names') or {}).values()), 'by_category': r['counts'], 'by_class': r['class_counts'], 'view_owned_elements': r['view_owned'], 'elements': r['stats']['elements_with_header']}
        if a.json: say(json.dumps(out, indent=1, sort_keys=True)); return 0     # sorted keys: diffable between saves
        if a.tsv:
            say('kind\tname\tcount')
            for k, v in r['counts'].items(): say('category\t%s\t%d' % (k, v))
            for k, v in r['class_counts'].items(): say('class\t%s\t%d' % (k, v))
            return 0
        say('elements with header: %d (%d owned by a view: 2D annotation/detail)' % (out['elements'], out['view_owned_elements']))
        say('by category:')
        for k, v in r['counts'].items(): say('  %8d  %s' % (v, k))
        kinds = {}
        for k, v in r['counts'].items():
            if k.startswith('(no category: '): kinds[k[14:].split(')')[0]] = kinds.get(k[14:].split(')')[0], 0) + v
        if kinds: say('without a Revit category (Revit API Category is null too): %d = %s' % (sum(kinds.values()), ', '.join('%s %d' % kv for kv in sorted(kinds.items(), key=lambda t: -t[1]))))
        sn = r.get('subcategory_names') or {}
        if sn: say('sub/user categories (resolved to their built-in parent above): %d = %s' % (len(sn), ', '.join(sorted(sn.values())[:12]) + (', ...' if len(sn) > 12 else '')))
    elif a.cmd == 'elements':
        for x in element_rows(r['arrays'], a.limit, json_=a.json): say(x)
    return 0


def element_rows(z, limit=0, json_=False):
    """text lines of the element table (TSV with a header, or a JSON array one element per line) from scan(...)['arrays']"""
    import json
    from . import categories as CT
    catn = _cat_table(); cn = [str(x) for x in z['cls_names']]
    n = len(z['id']); n = min(n, limit) if limit else n
    def row(i):
        c = int(z['cat'][i]); b = z['bbox'][i]; k = int(z['cls'][i])
        nm = catn.get(c, '')
        if c < -(1 << 61): c = -1; nm = '(no category: %s)' % CT.kind(cn[k] if k != 65535 else '')       # no category in the file (Revit API Category is null as well)
        return (int(z['id'][i]), cn[k] if k != 65535 else '', c, nm, int(z['owner_view'][i]), int(z['family'][i]), None if b[0] != b[0] else [float(v) for v in b])
    if json_:
        yield '['
        for i in range(n): yield json.dumps(dict(zip(('id', 'class', 'category_id', 'category', 'owner_view', 'family', 'bbox_ft'), row(i)))) + (',' if i + 1 < n else '')
        yield ']'; return
    yield 'id\tclass\tcategory\towner_view\tfamily\tbbox_ft(min xyz, max xyz)'
    for i in range(n):
        x = row(i); yield '%s\t%s\t%s\t%s\t%s\t%s' % (x[0], x[1], x[3] or x[2], '' if x[4] == -1 else x[4], '' if x[5] == -1 else x[5], ' '.join('%.3f' % v for v in x[6]) if x[6] else '')


def _query(a, say, log):
    import json
    if a.cmd in SUMMARY: return _summary(a, say, log)
    if a.cmd == 'walls-red-material':
        r = walls_red_material(a.file, workers=a.workers or None, log=log)
        if a.json: say(json.dumps({k: v for k, v in r.items() if k != 'red'}, indent=1, default=str)); return 0
        say('walls below 5 m with a red material: %d' % r['count']); say(json.dumps({k: v for k, v in r.items() if k not in ('rows', 'red', '_types', '_colors')}, default=str)); return 0
    q = dict(READY.get(a.cmd, {}))
    if a.cls: q['cls'] = a.cls.split(',')
    if a.category: q['category'] = a.category
    if a.cmd == 'collect' and not (a.cls or a.category): print('rvt-ballet query collect: give --class and/or --category', file=sys.stderr); return 2
    flds = [x for x in a.fields.split(',') if x]
    where = dict(w.split('=', 1) for w in a.where)
    rows = collect(a.file, q.get('cls'), q.get('category'), flds, where or None, workers=a.workers or None, log=log)
    cols = ['id', 'class', 'name', 'type_name', 'level', 'category'] + [k for k in flds if k not in ('id', 'class', 'name')]
    if a.json: say(json.dumps(rows, indent=1, default=str)); return 0
    if a.tsv: _tsv(cols, rows, say); return 0
    say('%s (%d):' % (a.cmd, len(rows)))
    for r in rows: say('  ' + ' | '.join('' if r.get(k) is None else str(r.get(k)) for k in cols))
    return 0


def main(argv, say=print):
    from . import stable; return stable.run(argv, _main, say)


def _main(argv, say=print):
    """rvt-ballet query COMMAND FILE [options]; exit 0 ok, 1 unreadable, 2 usage, 3 answer printed but compressed blocks fail their checksum (incomplete), 75 file changed during read (after RVT_Q_RETRIES retries)"""
    a = _parser().parse_args(argv)
    if not os.path.isfile(a.file): print('rvt-ballet: no such file: %s' % a.file, file=sys.stderr); return 2
    log = (lambda m: print(m, file=sys.stderr, flush=True)) if a.verbose else None
    tries = int(os.environ.get('RVT_Q_RETRIES', '2')); t0 = time.time()
    for k in range(tries + 1):
        lines = []
        try:
            rc = _query(a, lines.append, log)
        except FileChanged as ex:
            if k < tries: print('rvt-ballet: %s (retry %d of %d in 2 s)' % (ex, k + 1, tries), file=sys.stderr); time.sleep(2); continue
            print('rvt-ballet: %s' % ex, file=sys.stderr); return 75
        except (SystemExit, KeyboardInterrupt): raise
        except Exception as ex:
            if isinstance(ex, ValueError) and any(t in str(ex) for t in ('needs --class', 'unknown category', 'no schema class')): print('rvt-ballet: %s' % ex, file=sys.stderr); return 2
            try: consistent()                  # an error caused by a file being saved is a change, not damage
            except FileChanged as ex2:
                if k < tries: print('rvt-ballet: %s (retry %d of %d in 2 s)' % (ex2, k + 1, tries), file=sys.stderr); time.sleep(2); continue
                print('rvt-ballet: %s' % ex2, file=sys.stderr); return 75
            if os.environ.get('RVT_Q_TRACE'): raise
            print('rvt-ballet: cannot read %s: %s: %s' % (os.path.basename(a.file), type(ex).__name__, str(ex)[:300]), file=sys.stderr); return 1
        if _G.get('damaged') and k < tries and os.environ.get('RVT_Q_NO_DAMAGE_RETRY') != '1':
            print('rvt-ballet: %d compressed blocks fail their checksum (a save in progress can cause this): retry %d of %d in 2 s' % (_G['damaged'], k + 1, tries), file=sys.stderr); time.sleep(2); continue
        for x in lines: say(x)          # printed only after the file was found unchanged: a torn read never reaches stdout
        if log: log('total %.2fs' % (time.time() - t0))
        if _G.get('damaged') and not rc: return 3      # still failing after the retries: the answer above may be incomplete; a script must not take it for a clean result (stderr says why)
        return rc


if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
