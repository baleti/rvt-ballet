"""Save wiring: optional savegate adapter. Everything degrades to 'unavailable' when savegate is not installed."""
import os, sys

def _import():
    try:
        import savegate as sg
        return sg
    except ImportError:
        p = os.path.expanduser('~/src/savegate')
        if os.path.isdir(os.path.join(p, 'savegate')) and p not in sys.path:
            sys.path.insert(0, p)
            try:
                import savegate as sg
                return sg
            except ImportError:
                pass
    return None

_WORKER = r'''
import sys, os, pickle
a, o, lim, wl, here = sys.argv[1:6]
try:      # POSIX only: on Windows (no 'resource') the worker runs WITHOUT a memory cap (a Job Object would be needed)
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (int(lim), int(lim)))
except Exception:
    pass
sys.path[:0] = [here, wl, os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research')]
try:
    from savegate.adapters import RvtAdapter
    from savegate import rvt_elements
    ad = RvtAdapter(elements_fn=rvt_elements.elements); buf = open(a, 'rb').read(); snap = ad.snapshot(buf)
    res = ('ok', (snap, list(ad._keys)))
except MemoryError:
    res = ('MemoryError', '')
except Exception as e:
    res = (type(e).__name__, str(e)[:300])
pickle.dump(res, open(o + '.tmp', 'wb')); os.replace(o + '.tmp', o)      # atomic: a worker killed mid-write leaves no half result
'''


def _run_worker(argv, lim, timeout):
    """run the verification worker with captured text output. POSIX: the worker caps itself (RLIMIT_AS in _WORKER). Windows has no resource module, so the
    child is put in a Job Object with a per-process memory limit (plat.proc.popen_capped): a model that does not fit makes the worker raise MemoryError (-> TooBig), never the viewer."""
    import subprocess
    if sys.platform != 'win32':
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    from . import plat
    p = plat.proc.popen_capped(argv, lim / 2 ** 30, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate(); raise
    return subprocess.CompletedProcess(argv, p.returncode, out, err)


def _disk_dir():
    d = os.environ.get('RVTBALLET_SNAPSHOT_CACHE')
    if d == '0': return None
    from . import plat
    return os.path.expanduser(d) if d else os.path.join(plat.dirs.cache_dir('rvtballet'), 'snapshots')


def _file_digest(path):
    """sha256 of the file CONTENT (a touch / checkout / copy that keeps the bytes must not invalidate the snapshot cache; any byte change must). Not memoised on stat: a same-size rewrite inside one mtime tick would return a stale digest and weaken verification."""
    import hashlib
    try: return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:20]
    except OSError: return 'unreadable'


def _reader_stamp():
    """changes whenever the reader / write-lab code that produces the dump changes (a stale dump would weaken verification)"""
    import hashlib
    h = hashlib.sha256()
    for root in (os.path.expanduser(os.environ.get('SAVEGATE_RVT_LIB') or '~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research'), os.path.dirname(os.path.abspath(__file__)), os.path.expanduser('~/src/savegate/savegate'), os.path.expanduser('~/rvt-research/edit-lab')):
        try:
            for n in sorted(os.listdir(root)):
                if n.endswith('.py'): h.update(('%s:%s;' % (n, _file_digest(os.path.join(root, n)))).encode())
        except OSError: pass
    return h.hexdigest()[:16]


def _disk_get(key):
    """(snap, keys) cached on disk for this source sha256 and reader stamp, or None; any damage (short file, bad checksum, unpickle error) is a miss, never an error"""
    import hashlib, pickle
    d = _disk_dir()
    if not d: return None
    f = os.path.join(d, '%s-%s.pkl' % (key.hex(), _reader_stamp()))
    try:
        raw = open(f, 'rb').read()
        if len(raw) < 32 or hashlib.sha256(raw[32:]).digest() != raw[:32]: return None
        snap, keys = pickle.loads(raw[32:]); return snap, keys
    except Exception: return None


def _disk_put(key, snap, keys, keep=6):
    import hashlib, pickle
    d = _disk_dir()
    if not d: return
    try:
        os.makedirs(d, exist_ok=True); body = pickle.dumps((dict(snap), set(keys)), 4); f = os.path.join(d, '%s-%s.pkl' % (key.hex(), _reader_stamp())); t = f + '.%d.tmp' % os.getpid()
        with open(t, 'wb') as o: o.write(hashlib.sha256(body).digest() + body)
        os.replace(t, f)
        old = sorted((os.path.join(d, n) for n in os.listdir(d) if n.endswith('.pkl')), key=os.path.getmtime)
        for x in old[:-keep]: os.remove(x)
    except Exception: pass


def _cached_adapter():
    """RvtAdapter whose snapshot() is memoised by content hash (last 3 buffers): the source dump (~14 s on a 5.6k-element file) is taken once per loaded
    file instead of at every save; the output of a save is cached too, so after SAVE (overwrite) the new loaded bytes cost nothing."""
    import hashlib
    from savegate.adapters import RvtAdapter
    class CachedRvtAdapter(RvtAdapter):
        def _snapshot_in_worker(self, buf):
            """the element dump (the memory hog: GBs on real projects) runs in a child process under RLIMIT_AS: a model that does not fit kills the WORKER, the save is refused cleanly (TooBig) and the viewer / host are never at risk.
            Reader errors inside the worker come back as RuntimeError('<Type>: msg') (-> 'output_unreadable' as before)."""
            import subprocess, tempfile, pickle
            from ._vendor.rvtplat import mem
            lim = os.environ.get('RVTBALLET_SNAPSHOT_MEM_GB'); lim = float(lim) * 2 ** 30 if lim else max(mem.limit_gb(0.7) * 2 ** 30 - mem.rss_bytes(), 2 * 2 ** 30)
            d = tempfile.mkdtemp(prefix='rvtballet-snap-'); a = os.path.join(d, 'in.rvt'); o = os.path.join(d, 'out.pkl')
            try:
                with open(a, 'wb') as f: f.write(buf)
                r = _run_worker([sys.executable, '-c', _WORKER, a, o, str(int(lim)), os.path.expanduser(os.environ.get('SAVEGATE_RVT_LIB') or '~/rvt-research/write-lab'), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))], lim, float(os.environ.get('RVTBALLET_SNAPSHOT_TIMEOUT', '7200')))
                if os.path.exists(o):
                    try: kind, payload = pickle.load(open(o, 'rb'))
                    except Exception as e: raise RuntimeError('verification worker left an unreadable result (%s, exit %s)' % (type(e).__name__, r.returncode))
                    if kind == 'ok': self._keys = set(payload[1]); return payload[0]
                    if kind == 'MemoryError': raise TooBig('the element dump needs more than the %.1f GB allowed for it (RVTBALLET_SNAPSHOT_MEM_GB / RVTPLAT_MEM_GB): this model is too large to verify on this machine, nothing was written' % (lim / 2 ** 30))
                    raise RuntimeError('%s: %s' % (kind, payload))
                err = (r.stderr or '').lower()
                if r.returncode in (-6, -9) or 'memory' in err or 'alloc' in err:      # abort / SIGKILL under the address-space limit, or an allocator message
                    raise TooBig('the verification worker ran out of memory under its %.1f GB limit (it was stopped, exit %s): this model is too large to verify on this machine, nothing was written' % (lim / 2 ** 30, r.returncode))
                raise RuntimeError('verification worker failed (exit %s%s): the model could not be read back, nothing was written' % (r.returncode, ('; ' + (r.stderr or '').strip().splitlines()[-1][:100]) if (r.stderr or '').strip() else ''))      # a crash is NOT reported as too_big: the UI must not invite skipping the full verify for it
            except subprocess.TimeoutExpired:      # a cap that is too tight for the model makes the dump crawl (seen: 51 MB project at 5 GB, no result after 2 h) instead of failing: stop it, refuse, nothing written
                raise TooBig('the element dump did not finish within %s s under its %.1f GB limit (RVTBALLET_SNAPSHOT_TIMEOUT / RVTBALLET_SNAPSHOT_MEM_GB): the model could not be verified on this machine, nothing was written' % (os.environ.get('RVTBALLET_SNAPSHOT_TIMEOUT', '7200'), lim / 2 ** 30))
            finally:
                import shutil; shutil.rmtree(d, ignore_errors=True)

        def __init__(self, *a, **k): super().__init__(*a, **k); self._memo = []; self.report = lambda stage: None
        def snapshot(self, buf):
            snap = self._snapshot_core(buf); self._seen = (getattr(self, '_seen', []) + [snap])[-2:]; return snap      # savegate dumps source then output: remember both for extra_checks

        def extra_checks(self, manifest):
            """a DECLARED edit that left its element unchanged did not happen (savegate only fails on UNDECLARED changes; a declared-but-unchanged element is merely informational there). Found on a real project: two moves in
            different partitions of one multi-pass save returned 200 although the second element never moved. Refuse instead of reporting success."""
            sup = getattr(super(), 'extra_checks', None); inherited = list(sup(manifest) or []) if sup else []      # savegate's own rule (dirty_members): it was SHADOWED by this override, so it never ran
            seen = getattr(self, '_seen', []); self._seen = []
            if len(seen) < 2: return inherited
            a, b = seen
            return inherited + [('not_applied', k) for k in sorted(manifest.get('modified', ())) if k != 'el:0' and k in a and k in b and a[k] == b[k]]      # el:0 is declared as tolerance (id-0 ghost bucket), not as an edit

        def _snapshot_core(self, buf):
            key = hashlib.sha256(buf).digest()
            for k, snap, keys in self._memo:
                if k == key: self._keys = set(keys); return dict(snap)
            hit = _disk_get(key)
            if hit is not None:
                snap, keys = hit; self._keys = set(keys); self._memo = ([(key, dict(snap), set(keys))] + self._memo)[:3]; return dict(snap)
            self.report('reading %d MB (element dump for verification)' % (len(buf) >> 20))
            snap = (self._snapshot_in_worker(buf) if os.environ.get('RVTBALLET_SNAPSHOT_WORKER', '1') != '0' else super().snapshot(buf)); self._memo = ([(key, dict(snap), set(self._keys))] + self._memo)[:3]
            _disk_put(key, snap, self._keys)
            return snap
    return CachedRvtAdapter


class TooBig(Exception):
    """not enough memory budget to hold source + output + snapshots (measured ~8x the file size)"""


def element_rows(src):
    """decompressed Global/ElemTable bytes / 28 = rough element count (cheap: one stream). `src` is the file's bytes (already loaded by the save session) or a path; None when the write-lab modules are unavailable or the file cannot be parsed"""
    try:
        from .edit import WL
        if WL not in sys.path: sys.path.insert(0, WL)
        import cfb, rvtw
        if not isinstance(src, (bytes, bytearray)):
            with open(src, 'rb') as f: src = f.read()
        P = bytes(rvtw.Stream(cfb.CFB(bytes(src)).streams()['Global/ElemTable'].data).payload)
        return sum(r for (_, _, r) in rvtw.members(P, P.find(rvtw.GZ))) // 28
    except Exception:
        return None


def check_memory(path, buf=None):
    """refuse BEFORE opening when the element-level verify would not fit: need = max(9 x file size, KB-per-row x element rows). Measured on real 2024 projects: a 24 MB file with ~26k rows used ~4.5 GB+
    (~170 KB/row) while a padded 305 MB container with 5.6k rows used 2.4 GB: memory follows element count / geometry, not file size. 200 KB/row is deliberately conservative (refusing is safe, running out of memory is not)."""
    from ._vendor.rvtplat import mem
    size = os.path.getsize(path); need = size * float(os.environ.get('RVTBALLET_SAVE_MEM_FACTOR', '9')); rows = element_rows(buf) if buf is not None else None      # rows come from the bytes the session already holds: no second read of the file
    if rows: need = max(need, rows * float(os.environ.get('RVTBALLET_SAVE_MEM_PER_ROW_KB', '200')) * 1024)
    budget = mem.limit_gb(0.7) * 2 ** 30 - mem.rss_bytes()
    if need > budget:
        raise TooBig('saving this %.0f MB file (about %s elements) needs roughly %.1f GB of memory but only %.1f GB is available to the viewer (raise RVTPLAT_MEM_GB or close other programs)'
                     % (size / 2 ** 20, '%d' % rows if rows else '?', need / 2 ** 30, max(budget, 0) / 2 ** 30))


class SaveSessions:
    """one savegate Doc per model id, opened lazily from the source .rvt (fingerprint taken at first use = load time)"""
    def __init__(self, cfg=None):
        self.docs = {}; self.ed = {}; self.busy = set(); self.progress = {}; self.applied = {}; self.derived = {}; import threading; self._lk = threading.RLock(); self._cfg = cfg
    @property
    def cfg(self):
        """Config(allow_overwrite from env RVTBALLET_ALLOW_OVERWRITE=1; the oracle gate stays on)"""
        if self._cfg is not None: return self._cfg
        sg = _import()
        return sg.Config(allow_overwrite=os.environ.get('RVTBALLET_ALLOW_OVERWRITE') == '1') if sg else None
    @property
    def available(self): return _import() is not None
    def doc(self, mid, src, precheck=True):
        with self._lk: return self._doc(mid, src, precheck)
    def _doc(self, mid, src, precheck=True):
        sg = _import()
        if sg is None: raise RuntimeError('savegate is not installed')
        d = self.docs.get(mid)
        if d is None or d.path != os.path.abspath(src):
            pass      # the memory estimate is enforced when a non-limited save starts (save_as / save_overwrite), not at open
            if d is not None: d.close(); self.docs.pop(mid, None)       # replaced: do not leak its journal
            from savegate import rvt_elements
            d = sg.open_doc(src, _cached_adapter()(elements_fn=rvt_elements.elements), cfg=self.cfg)      # element-level verify
            if d.version == '?':          # an explicit adapter skips pick_adapter's refusal of non-Revit bytes
                d.close()
                if open(src, 'rb').read(8) == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': raise SourceDamaged('the model file is damaged (an OLE container whose Revit streams cannot be read); nothing was written')
                raise sg.UnsupportedVersion('%s is not a Revit file (unknown format, nothing can be saved)' % os.path.basename(src))
            self.docs[mid] = d
        return d
    def edits(self, mid):
        from .edit import Edits
        return self.ed.setdefault(mid, Edits())
    def info(self, mid, src):
        if not src or not os.path.exists(src): return {'available': self.available, 'open': False}
        if not self.available: return {'available': False, 'open': False}
        try: d = self.doc(mid, src)
        except Exception as e: return {'available': True, 'open': False, 'error': str(e)}
        fp = d.fingerprint
        return {'available': True, 'open': True, 'version': d.version, 'size': fp.size, 'sha256': fp.sha256[:12]}
    def close(self, mid=None):
        for k in ([mid] if mid else list(self.docs)):
            d = self.docs.pop(k, None)
            if d: d.close()


_MEMBER_WORKER = r"""
import sys, os, re, json
sys.path[:0] = [os.path.expanduser('~/rvt-research')]
import rvt_xcache
x = rvt_xcache.get_x_ro(sys.argv[1]); want = set(json.load(open(sys.argv[2])))
ids = lambda v: [int(m) for m in re.findall(r'\d+', str(v))]
def find(o, key, res):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: res.append(v)
            else: find(v, key, res)
    elif isinstance(o, list):
        for v in o: find(v, key, res)
members = {}      # element id -> group ids: ElementGroup.m_pElemIdsPairSet lists the members; the group instance is itself flagged
for (e, c), r in x['recs'].items():
    if c != 'ElementGroup': continue
    mm = []; find(r.get('fields'), 'm_pElemIdsPairSet', mm); mem = []
    for v in mm: find(v, 'm_elementId', mem)
    for m in mem:
        for i in ids(m): members.setdefault(i, set()).add(e)
    members.setdefault(e, set()).add(e)
out = {}; hosting = {}      # host id -> elements whose m_hostId names it (a moved host leaves them behind: Revit's own MoveElement drags them along)
for (e, c), r in x['recs'].items():
    h = []; find(r.get('fields'), 'm_hostId', h)
    for v in h:
        for i in ids(v):
            if i < 2 ** 32 - 1 and i != e: hosting.setdefault(i, set()).add(e)
leveled = {}      # level id -> elements associated with it (m_assocLevelId / m_levelId / m_upperLevelId): Revit moves level-relative elements with a moved level, the writer moves the Level record only
for (e, c), r in x['recs'].items():
    if c == 'Level': continue
    for key in ('m_assocLevelId', 'm_levelId', 'm_upperLevelId'):
        t = []; find(r.get('fields'), key, t)
        for v in t:
            for i in ids(v):
                if i < 2 ** 32 - 1 and i != e: leveled.setdefault(i, set()).add(e)
dimmed = {}      # element id -> dimensions whose witness geomRef (m_elemId) names it (a moved wall leaves the dimension value stale until Revit regenerates)
for (e, c), r in x['recs'].items():
    if 'Dim' not in c: continue
    t = []; find(r.get('fields'), 'm_elemId', t)
    for v in t:
        for i in ids(v):
            if i < 2 ** 32 - 1 and i != e: dimmed.setdefault(i, set()).add(e)
for (e, c), r in x['recs'].items():
    if e not in want: continue
    d = []; find(r.get('fields'), 'm_designOptionId', d); h = []; find(r.get('fields'), 'm_hostId', h)
    out.setdefault(str(e), []).append({'cls': c, 'groups': sorted(members.get(e, ())), 'options': [i for v in d for i in ids(v) if i < 2 ** 31], 'hosts': [i for v in h for i in ids(v) if i < 2 ** 32 - 1], 'hosting': len(hosting.get(e, ())), 'dimmed': len(dimmed.get(e, ())), 'leveled': len(leveled.get(e, ()))})
print(json.dumps(out))
"""


def membership(buf, eids):
    """{eid: [reasons]} for the edited elements: member of a group (m_groupId names an ElementGroup) or of a design option (m_designOptionId is a real id).
    Raises when the records cannot be read (callers treat that as 'unknown': refuse the in-place save)."""
    import subprocess, tempfile, json
    d = tempfile.mkdtemp(prefix='rvtballet-mem-')
    try:
        p = os.path.join(d, 'm.rvt')
        with open(p, 'wb') as f: f.write(buf)
        ip = os.path.join(d, 'ids.json')
        with open(ip, 'w') as f_ids: json.dump(sorted(int(e) for e in eids), f_ids)      # a file, not argv: a long id list exceeds the argument limit
        r = subprocess.run([sys.executable, '-c', _MEMBER_WORKER, p, ip], capture_output=True, text=True, timeout=1800)
        if r.returncode: raise RuntimeError('group/design-option check failed: ' + (r.stderr.strip().splitlines() or ['?'])[-1][:150])
        res = {}
        for e, recs in json.loads(r.stdout.strip().splitlines()[-1]).items():
            why = sorted({'group %d' % g for x in recs for g in x['groups']} | {'design option %d' % o for x in recs for o in x['options']} | {'hosted on %d' % h for x in recs for h in x.get('hosts', [])} | {'hosts %d element(s)' % n for x in recs for n in [x.get('hosting', 0)] if n} | {'dimensioned by %d dimension(s)' % n for x in recs for n in [x.get('dimmed', 0)] if n} | {'level constrains %d element(s)' % n for x in recs for n in [x.get('leveled', 0)] if n and x.get('cls') == 'Level'})
            if why: res[int(e)] = why
        return res
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)


class Workshared(Exception):
    """in-place save of a workshared (central/local) model: the file carries worksets and a central link the writer does not maintain"""


def worksharing_state(buf):
    """BasicFileInfo 'Worksharing:' value ('Not enabled', 'Central', 'Local', ...) or None when it cannot be read"""
    import re, sys
    lib = os.environ.get('SAVEGATE_RVT_LIB') or os.path.expanduser('~/rvt-research/write-lab')
    if lib not in sys.path: sys.path.insert(0, lib)
    try:
        import cfb
        d = cfb.CFB(buf).streams()['BasicFileInfo'].data
    except Exception: return None
    for off in (0, 1):                     # the UTF-16 text starts at an odd offset in some years
        m = re.search(r'Worksharing:\s([^\r\n]*)', d[off:].decode('utf-16le', 'ignore'))
        if m: return m.group(1).strip()
    return None


class SourceDamaged(Exception):
    """the source holds a gzip member whose stored CRC32/ISIZE does not match its content (c7x-rvtwrite 2026-11-01: edited saves used to carry such a member silently)"""


def _ecc_bad_pages(d, rvtw):
    """indices of stored pages whose ECC fails (same test as the savegate gate); [] for XML/raw gzip streams or when ecc is unavailable"""
    try: import ecc
    except ImportError: return []
    if d[:5] == b'<?xml' or d[:2] == b'\x1f\x8b': return []
    full = len(d) // rvtw.PAGE_STORED
    pg = [d[i * rvtw.PAGE_STORED:(i + 1) * rvtw.PAGE_STORED] for i in range(full)]
    try: ok = ecc.check_many(pg) if pg else []
    except AttributeError: ok = [ecc.check(q) for q in pg]
    bad = [i for i in range(full) if not ok[i]]; last = d[full * rvtw.PAGE_STORED:]
    if last and (ecc.params(len(last)) is None or not ecc.check(last)): bad.append(full)
    return bad


def _cfb_structure_bad(buf, ssz, nsec, nfat, dstart, ndif):
    """c7x-rvtread 98/100: VM-refused (Revit 2024) CFB header/directory flips the reader tolerates: FAT sector count (0x2c), first directory sector (0x30), first mini-FAT sector (0x3c), root entry type, sibling/child index out of range. Only the plain single-header case (no DIFAT) is checked."""
    import struct
    out = []
    try:
        if ndif != 0: return out
        if nfat > 109: return [('CFB header (FAT sector count)', 0)]
        per = ssz // 4
        fat = []
        for i in range(nfat):
            sec = struct.unpack_from('<I', buf, 76 + 4 * i)[0]
            if sec >= nsec: return out
            fat.extend(struct.unpack_from('<%dI' % per, buf, (sec + 1) * ssz))
        if sum(1 for e in fat if e == 0xFFFFFFFD) != nfat: out.append(('CFB header (FAT sector count)', 0))
        def chain(st):
            c, seen = [], set()
            while st < 0xFFFFFFFA:
                if st in seen or st >= len(fat): return None
                seen.add(st); c.append(st); st = fat[st]
            return c if st == 0xFFFFFFFE else None
        dch = chain(struct.unpack_from('<I', buf, 48)[0])
        if dch is None: out.append(('CFB header (directory start sector)', 0)); return out
        mstart, mcount = struct.unpack_from('<I', buf, 60)[0], struct.unpack_from('<I', buf, 64)[0]
        mch = chain(mstart) if mstart != 0xFFFFFFFE else []
        if mch is None or len(mch) > mcount:      # fewer than the header count is tolerated by Revit 2024 (VM, hdr3 0x40)
            out.append(('CFB header (mini-FAT start sector)', 0))
        raw = b''.join(buf[(c + 1) * ssz:(c + 2) * ssz] for c in dch)
        n = len(raw) // 128
        ent = [(raw[128 * i + 66], raw[128 * i + 67]) + struct.unpack_from('<III', raw, 128 * i + 68) for i in range(n)]      # type, color, left, right, child
        if not ent or ent[0][0] != 5: out.append(('CFB directory (root entry type)', 0)); return out
        bad_idx = any(any(x != 0xFFFFFFFF and x >= n for x in ((l, r, ch) if t != 2 else (l, r))) for t, c, l, r, ch in ent[1:]) or (ent[0][4] != 0xFFFFFFFF and ent[0][4] >= n)      # a stream's child field is unused: Revit 2024 opened dir_e2_child (VM)
        if bad_idx:
            out.append(('CFB directory (entry field)', 0)); return out      # VM: root left/right/color and any entry color are tolerated, so only child/sibling indices past the table are flagged
        owner = {}      # c7x-rvtread 102: cross-linked / short / overlong FAT chains of big streams that still parse
        for i in range(n):
            if raw[128 * i + 66] not in (2, 5): continue      # 5 = root: its chain is the mini stream container
            st, sz = struct.unpack_from('<I', raw, 128 * i + 116)[0], struct.unpack_from('<Q', raw, 128 * i + 120)[0]
            if sz < 4096 and i != 0: continue
            if i == 0 and sz == 0: continue
            ch = chain(st)
            if ch is None or len(ch) * ssz < sz or (len(ch) - 1) * ssz >= sz or any(owner.setdefault(c, i) != i for c in ch):
                out.append(('CFB FAT chain (stream %d)' % i, 0)); break
        for c in dch + (mch or []):
            if owner.setdefault(c, -1) != -1: out.append(('CFB FAT chain (directory overlaps stream)', 0)); break
        seen, stack = set(), [ent[0][4]]
        while stack:
            x = stack.pop()
            if x == 0xFFFFFFFF: continue
            if x in seen: out.append(('CFB directory (tree cycle)', 0)); break
            seen.add(x); stack += [ent[x][2], ent[x][3]]
            if ent[x][0] in (1, 5) and ent[x][4] != 0xFFFFFFFF: stack.append(ent[x][4])
    except Exception:
        pass
    return out


def source_damage(buf):
    """[(stream, member index)] of CRC-bad independent gzip members in the Partitions/* streams; [] when clean or when the check cannot run (a lower bound: gzcheck walks only the members it can frame; 0 false positives on 101 real partition streams of 77 corpus files)"""
    out = []
    try:
        import struct
        if len(buf) >= 28 and struct.unpack_from('<H', buf, 26)[0] not in (3, 4):      # c7x-rvtread 94: major-version high byte flipped; the reader loads it, Revit 2024 refuses (COleException 0x80030105)
            out.append(('CFB header (major version)', 0))
        # c7x-rvtread 97: VM verdicts on single-byte header flips (Revit 2024 refuses, reader loads): minicutoff 0x38..0x3b, minishift 0x20, DIFAT start 0x44 (no DIFAT sectors), unused DIFAT entries 0x60..0x1f0 not FREESECT
        if len(buf) >= 512 and buf[:8] == bytes.fromhex('d0cf11e0a1b11ae1'):
            ms, cut, nfat, dstart, ndif = struct.unpack_from('<H', buf, 32)[0], struct.unpack_from('<I', buf, 56)[0], struct.unpack_from('<I', buf, 44)[0], struct.unpack_from('<I', buf, 68)[0], struct.unpack_from('<I', buf, 72)[0]
            if ms != 6: out.append(('CFB header (mini sector shift)', 0))
            if buf[8:24] != bytes(16) or buf[34:40] != bytes(6) or struct.unpack_from('<I', buf, 52)[0] != 0 or struct.unpack_from('<H', buf, 28)[0] != 0xFFFE:      # c1x-rvtsave 182: single-byte flips here (CLSID, reserved, transaction signature, byte order) were accepted; 45 of 45 Revit-made corpus files have them zero / 0xFFFE
                out.append(('CFB header (reserved/CLSID/byte order)', 0))
            if cut != 4096: out.append(('CFB header (mini stream cutoff)', 0))
            if ndif == 0 and dstart != 0xFFFFFFFE: out.append(('CFB header (DIFAT start)', 0))
            ssz = 1 << struct.unpack_from('<H', buf, 30)[0] if struct.unpack_from('<H', buf, 30)[0] in (9, 12) else 512
            nsec = max(1, len(buf) // ssz)
            if ndif > nsec or (ndif and dstart >= nsec): out.append(('CFB header (DIFAT sector count)', 0))      # c5x-rvtread: offset 72 flip, Revit 2024 'docfile has been corrupted'
            if nfat <= 109 and ndif == 0:      # c5x-rvtread: offset 76 flip, Revit 2024 'document can not be opened'; every listed FAT sector must be marked FATSECT (0xFFFFFFFD) inside the FAT itself
                per = ssz // 4
                dif = [struct.unpack_from('<I', buf, 76 + 4 * i)[0] for i in range(nfat)]
                def fatent(e):
                    k = e // per
                    if k >= nfat or dif[k] >= nsec: return None
                    off = (dif[k] + 1) * ssz + 4 * (e % per)
                    return struct.unpack_from('<I', buf, off)[0] if off + 4 <= len(buf) else None
                if any(e >= nsec or fatent(e) != 0xFFFFFFFD for e in dif): out.append(('CFB header (FAT sector index)', 0))
                else:      # c1x-rvtsave 183: one-byte flips of 'number of directory sectors' (v4) and 'number of mini FAT sectors' were accepted; both must equal the chain length (678 of 678 local files do)
                    def clen(s0):
                        n, s = 0, s0
                        while s < 0xFFFFFFFA and n <= nsec:
                            n += 1; s = fatent(s)
                            if s is None: return -1
                        return n
                    major, nd, ds, mst, nmini = struct.unpack_from('<H', buf, 26)[0], struct.unpack_from('<I', buf, 40)[0], struct.unpack_from('<I', buf, 48)[0], struct.unpack_from('<I', buf, 60)[0], struct.unpack_from('<I', buf, 64)[0]
                    if (nd != (clen(ds) if major == 4 else 0)) or nmini != (clen(mst) if mst < 0xFFFFFFFA else 0): out.append(('CFB header (directory/mini FAT sector count)', 0))
            if ndif == 0 and nfat <= 109 and any(struct.unpack_from('<I', buf, 76 + 4 * i)[0] != 0xFFFFFFFF for i in range(nfat, 109)):
                out.append(('CFB header (unused DIFAT entry)', 0))
            out.extend(_cfb_structure_bad(buf, ssz, nsec, nfat, dstart, ndif))
    except Exception:
        pass
    try:      # c7x-rvtread 96: BasicFileInfo has no checksum; a damaged '.' of the stored path extension makes Revit 2024 say 'not a valid .rte file' (0 of 78 corpus files lack the extension)
        import re
        from .edit import WL
        if WL not in sys.path: sys.path.insert(0, WL)
        import cfb
        bfi = cfb.CFB(bytes(buf)).streams().get('BasicFileInfo')
        if bfi is not None and not re.search(r'\.(rvt|rte|rfa|rft)', bytes(bfi.data).decode('utf-16le', 'ignore'), re.I):
            out.append(('BasicFileInfo (path extension)', 0))
        elif bfi is not None:      # c7x-rvtread 110: Revit 2024 'internal error' when the flag byte before the 'Autodesk Revit' string (offset j-5, always 0 in 117 files) is flipped; its u32 length (j-4) is 14..300
            _d = bytes(bfi.data); _j = _d.find('Autodesk Revit'.encode('utf-16le'))
            if _j >= 5 and (_d[_j - 5] != 0 or not 14 <= int.from_bytes(_d[_j - 4:_j], 'little') <= 300): out.append(('BasicFileInfo (structure)', 0))
    except Exception:
        pass
    try:
        from .edit import WL
        if WL not in sys.path: sys.path.insert(0, WL)
        import cfb, rvtw
        from .gzcheck import member_report
        try: _streams = cfb.CFB(bytes(buf)).streams()
        except Exception:      # c7x-rvtread 101: a FAT chain loop/flip made the walk raise and source_damage reported [] (clean); an unparseable container is damage
            if bytes(buf[:8]) == bytes.fromhex('d0cf11e0a1b11ae1'): out.append(('CFB (FAT chain unreadable)', 0))
            return out
        for k, v in _streams.items():
            if k.startswith('Partitions/'):
                out.extend((k, i) for i in member_report(bytes(rvtw.Stream(v.data).payload))[1])
                out.extend((k + ' (page ECC)', i) for i in _ecc_bad_pages(v.data, rvtw))      # c7x-rvtread 62: zeroed/flipped bytes that gzip does not see
            elif k not in rvtw.PLAIN and not k.startswith('\x05') and k != 'Formats/Latest':
                if k.startswith('Global/'): out.extend((k + ' (gzip CRC)', i) for i in member_report(bytes(rvtw.Stream(v.data).payload))[1])      # c7x-rvtread 106: a flip inside Global/ElemTable etc. with the page ECC restamped passed every check; 0 of 360 clean Global streams (60 files) fail the member CRC      # c7x-rvtread 68: the other paged streams (Global/*, Contents..) carry page ECC too; the savegate gate checks them, SAVE AS did not
                out.extend((k + ' (page ECC)', i) for i in _ecc_bad_pages(v.data, rvtw))
        return out
    except Exception:
        return out


def _refuse_damaged(d):
    bad = source_damage(d.buf)
    if bad: raise SourceDamaged('refused: the source file is already damaged (%d compressed block(s) in %s fail their checksum), so saving would carry the damage into the copy. Nothing was written.' % (len(bad), ', '.join(sorted({k for k, _ in bad}))))


class DiskError(Exception):      # maps to 507 disk_error in the server (same name as the savegate library's)
    pass


class GroupOrOption(Exception):
    """in-place save of an edit that touches a group (member or instance) or a design-option element"""


class OutputUnreadable(Exception):
    """the reader crashed while re-reading the produced bytes: the output is not trustworthy, nothing was written"""


def _guard(fn, *a, **k):
    sg = _import()
    try: return fn(*a, **k)
    except (sg.SaveError, OSError, TooBig): raise
    except Exception as e:
        raise OutputUnreadable('the edited file could not be read back (%s: %s); nothing was written' % (type(e).__name__, e)) from e


def error_status(exc):
    """savegate exception -> (http status, machine code)"""
    n = type(exc).__name__
    if n == 'Bad' and 'no layout fits' in str(exc): return (409, 'source_damaged')      # writer could not lay out a damaged source
    return {'Conflict': (409, 'conflict'), 'GateClosed': (409, 'gate_closed'), 'OverwriteDisabled': (409, 'overwrite_disabled'),
            'Exists': (409, 'exists'), 'SaveError': (409, 'refused'), 'Locked': (423, 'locked'), 'VerifyFailed': (422, 'verify_failed'),
            'EditError': (400, 'edit_error'), 'LightVerifyFailed': (422, 'verify_failed'), 'LayoutChanged': (409, 'layout_changed'), 'TooBig': (507, 'too_big'), 'OutputUnreadable': (422, 'output_unreadable'), 'BadDest': (400, 'bad_dest'), 'StaleEdits': (409, 'stale_edits'), 'Workshared': (409, 'workshared'), 'ReadOnlyTarget': (409, 'read_only'), 'GroupOrOption': (409, 'group_or_option'), 'SourceDamaged': (409, 'source_damaged'), 'CloudPlaceholder': (409, 'cloud_placeholder'), 'NetworkFS': (409, 'network_fs'), 'UnsupportedVersion': (415, 'unsupported_version'), 'DiskError': (507, 'disk_error')}.get(n, (500, 'error'))


_UNTOUCHED = ("untouched", "not touched", "unchanged", "nothing was written", "nothing written", "not changed", "nothing was replaced", "not written")


def user_message(exc, status=None):
    """refusal text for the user: the error plus a plain statement that no file was changed (unless it already says so). Not for 5xx after the write started."""
    m = str(exc).rstrip(". ")
    if "after rename" in m: return m + ". The file on disk WAS replaced and may be damaged; use RESTORE to bring back the previous version (the backup was made before the save)"      # found wrong after the replace: never claim it is untouched
    if any(w in m.lower() for w in _UNTOUCHED): return m
    return m + ("; the model file was not touched" if (status or 0) < 500 or type(exc).__name__ == "DiskError" else "")


def result_json(r):
    out = {'ok': True, 'dest': r.dest, 'size': r.size, 'sha256': r.sha256[:12], 'backup': r.backup, 'version': r.version,
           'elapsed': round(r.elapsed, 3), 'verify': r.report}
    w = [str(x) for x in ((r.report or {}).get('warnings') or [])]      # e.g. 'another program changed the file in the last moment before it was replaced': must reach the user, not stay inside verify
    if w: out['warnings'] = w
    return out


def _stage(ss, mid, text):
    import time
    p = ss.progress.setdefault(mid, {'t0': time.time()}); p['stage'] = text; p['t'] = time.time()


def _drop_reader_caches():
    """the reader libraries keep per-path state (decoded records) that a save never reuses: every apply / read-back works on a fresh temp path"""
    for mn, names in (('rvt_geometry', ('_ctx', '_docs')), ('rvt_fast', ('_SHARED', '_G103', '_W'))):
        m = sys.modules.get(mn)
        for n in names:
            c = getattr(m, n, None) if m else None
            if isinstance(c, dict): c.clear()


def _refuse_bad_output(nb):
    """c7x-rvtread 107: the writer's own output must pass the same CFB header/directory/FAT-chain structure check as a source (5 ms); a broken container is never written"""
    import struct
    b = bytes(nb)
    if len(b) < 512 or b[:8] != bytes.fromhex('d0cf11e0a1b11ae1'): return
    ssz = 1 << struct.unpack_from('<H', b, 30)[0] if struct.unpack_from('<H', b, 30)[0] in (9, 12) else 512
    bad = _cfb_structure_bad(b, ssz, max(1, len(b) // ssz), struct.unpack_from('<I', b, 44)[0], 0, struct.unpack_from('<I', b, 72)[0])
    if bad: raise OutputUnreadable('the edited file has a damaged container structure (%s); nothing was written' % bad[0][0])


def _pending(ss, mid, d, new_bytes, manifest, light=False):
    """bytes + manifest of the recorded edits replayed on the loaded bytes (explicit new_bytes win). light=True (limited verification of models too big for the element dump): the full reader read-back and the derived-echo scan
    (two whole-model reader dumps, 10+ GB on a 64 MB project) are replaced by a record-level read-back of the edited elements only"""
    if new_bytes is not None: return new_bytes, manifest or {}
    from .edit import apply_full, Edits
    from .edit import compose
    e = ss.edits(mid); ops = list(e.ops); ss.applied[mid] = len(ops)
    nb, deleted = apply_full(d.buf, ops); m = Edits(); m.ops = ops; cops = compose(ops)
    if light: _light_readback(d.buf, nb, cops)
    else: _readback(d.buf, nb, cops)
    mf = m.manifest(deleted); echoes = [] if light else derived_echoes(d.buf, nb, cops)
    from .edit import last_dirty_members, BACKEND
    dm = last_dirty_members() if BACKEND() == 'rvtedit' and os.environ.get('RVTBALLET_DIRTY_MEMBERS', '1') == '1' else None
    _drop_reader_caches()
    if dm: mf['dirty_members'] = dm      # savegate refuses any member outside this set that differs from the source
    if dm and len(cops) == 1 and cops[0].get('op') in ('move', 'rotate', 'set_num') and os.environ.get('RVTBALLET_SPAN_RULE', '1') == '1': mf['member_span_max'] = 2048 if str(getattr(d, 'version', '2024')) in ('2024', '2025', '2026') else 8192      # one same-length placement edit: the changed bytes of a member stay in one small window (measured <= 531 B); a flip elsewhere in the member is refused
    if dm and cops and all(c.get('op') in ('move', 'rotate', 'set_string', 'set_num', 'delete', 'change_type', 'set_type_num') for c in cops) and os.environ.get('RVTBALLET_FROZEN_STREAMS', '1') == '1':
        mf['frozen_streams'] = True
        if any(c.get('op') == 'delete' for c in cops): mf['frozen_except'] = ['Global/ElemTable']      # delete drops the element from the element table (measured: the only non-partition stream that changes)      # these ops never touch a non-partition stream (measured: ws_move, ws_mark, ws_level outputs identical in every Global/* stream, BasicFileInfo, Contents, Formats); the gate then requires them byte-identical (a flip in Global/DocumentIncrementTable was ACCEPTED before)
    if mf.get('member_span_max') and len(cops) == 1 and cops[0].get('op') in ('move', 'rotate') and os.environ.get('RVTBALLET_DIFF_BUDGET', '1') == '1': mf['member_diff_bytes_max'] = 256 if cops[0].get('op') == 'move' else 768; mf['member_diff_runs_max'] = 16 if cops[0].get('op') == 'move' else 40
    if dm and len(cops) == 1 and cops[0].get('op') == 'set_string' and os.environ.get('RVTBALLET_SPAN_RULE', '1') == '1': mf['member_span_max'] = 8192 + 2 * len(str(cops[0].get('value', '')))      # string edit re-lays the record out: measured prefix/suffix windows: HVAC 1087-2422, Structural 2024 4794-6248 (25 elements in 3 files), 400 same length; widest 6248, a false refusal is the safe direction
    _declare_bucket0(mf)
    if echoes: mf['modified'] = sorted(set(mf['modified']) | {'el:%d' % i for i in echoes}); ss.derived[mid] = len(echoes)
    else: ss.derived.pop(mid, None)
    return nb, mf


def _declare_bucket0(mf):
    """id-0 bucket: records the reader decodes with id 0 are heuristic ghosts that overlap the writer's patched placement/field copies, so their decode flips whenever nearby bytes change (real 2024 file f31: el:0 changed on every
    edit although Revit opens the output clean and reads it correctly). The byte-level bounds (dirty_members + member_span_max) stay the safety net for them, so the bucket is declared only when those bounds are active."""
    if mf.get('member_span_max') and mf.get('dirty_members') and os.environ.get('RVTBALLET_BUCKET0', '1') == '1': mf['modified'] = sorted(set(mf.get('modified', ())) | {'el:0'})
    return mf


def _light_readback(src_buf, nb, ops):
    """read-back of the edited elements at RECORD level, without the reader's whole-model dump: for every by-name parameter edit, the element's parameter entries (name, value) before and after must be the same list except
    for exactly one VALUE entry (the edited one). Catches the 'edit left the element with half of its parameters' class (QUEUE severity-1 emoji case) on models where the full read-back does not fit in memory."""
    tg = [o for o in ops if o.get('op') in ('set_string', 'set_num') and o.get('param')]
    if not tg: return
    sg = _import(); import tempfile, shutil
    from . import edit as _ed
    for p in (_ed.EL, _ed.WL, os.path.expanduser('~/rvt-research')):
        if p not in sys.path: sys.path.insert(0, p)
    os.environ.setdefault('RVT_GEOM', '1')
    import rvtedit
    d = tempfile.mkdtemp(prefix='rvtballet-lrb-'); a = os.path.join(d, 'a.rvt'); b = os.path.join(d, 'b.rvt'); bad = []; saved = os.environ.get('PART')
    try:
        open(a, 'wb').write(src_buf); open(b, 'wb').write(nb)
        for o in tg:
            os.environ.pop('PART', None); probe = rvtedit.Edit(a); lp = probe.latest_partition(o['eid']); del probe
            if lp: os.environ['PART'] = str(lp)
            def entries(f):
                ed = rvtedit.Edit(f); log = ed.g.e.trace(o['eid'])[3]; r = [(l[1], str(l[4])) for l in log if l[1].startswith('ParamValue') and l[1].endswith(('.m_value', '.m_paramId'))]; del ed; return r
            try: x, y = entries(a), entries(b)
            except Exception as e: bad.append('element %d: could not be read back at record level (%s)' % (o['eid'], type(e).__name__)); continue
            diff = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
            if len(x) != len(y): bad.append('element %d lost or gained parameter entries (%d -> %d)' % (o['eid'], len(x), len(y)))
            elif len(diff) != 1 or not x[diff[0]][0].endswith('.m_value'): bad.append('element %d: %d parameter entries changed (exactly one value entry may)' % (o['eid'], len(diff)))
    finally:
        shutil.rmtree(d, ignore_errors=True)
        if saved is None: os.environ.pop('PART', None)
        else: os.environ['PART'] = saved
    if bad: raise sg.VerifyFailed('record-level read-back of the edited element(s) failed: %s' % '; '.join(bad[:3]), {'n_unexpected': len(bad), 'unexpected': bad[:20]})


def _note_derived(ss, mid, r):
    n = ss.derived.pop(mid, 0)
    if n: r.setdefault('warnings', []).append('%d other element(s) show the edited parameter too (the reader derives it from the edited element, e.g. a view\'s Detail Level on its viewports): they were declared as changed together with the edit' % n)


def expectations(ops, deleted=None):
    """what a successful save promises, in a form an INDEPENDENT checker (tools/rvt_expect_check.py: Revit API readback) can replay: per element, a parameter value, a location shift (feet), a rotation (degrees)
    or absence. From the composed ops, so a move +2 / -2 that cancels is not promised."""
    from .edit import compose
    out = []
    for o in compose(list(ops)):
        e = o['eid']
        if o['op'] == 'set_num' and o.get('param'): out.append({'eid': e, 'kind': 'param', 'name': o['param'], 'value': o['value'], 'type': o.get('kind', 'Double')})
        elif o['op'] == 'set_string' and o.get('param'): out.append({'eid': e, 'kind': 'param', 'name': o['param'], 'value': o['value'], 'type': 'String'})
        elif o['op'] == 'move': out.append({'eid': e, 'kind': 'move', 'd': [o['dx'], o['dy'], o['dz']]})
        elif o['op'] == 'rotate': out.append({'eid': e, 'kind': 'rotate', 'deg': o['deg']})
    for e in (deleted or []): out.append({'eid': int(e), 'kind': 'absent'})
    return out


import re as _re
_VIEWNAME_KEYS = {'View Name', 'View Name|String', 'Panel Schedule Name', 'Sheet Name'}
_LOCMARK_KEYS = {'Column Location Mark', 'Column Location Mark|String'}
_LEVELNAME_KEYS = {'Associated Level', 'Associated Level|String', 'Level', 'Level|String'}     # bare level name echoes (views' Associated Level, elements' Level)
_LEVELREF_KEYS = {'Work Plane|String', 'Host|String', 'Work Plane', 'Host'}
_ECHO_ALIAS = {'Name': ('View Name',), 'View Name': ('Name',)}


_LEVELELEV_KEYS = {'Elevation from Level', 'Coefficient of Utilization', 'Offset From Attachment At Top'}


def _offset_echo(n, x, y):
    """{'Unconnected Height|Double'} when the edited parameter is Top Offset / Base Offset and that derived height changed by exactly +delta / -delta (strict, 1e-6); else empty"""
    k = 'Unconnected Height|Double'
    if n not in ('Top Offset', 'Base Offset') or not all(isinstance(v, float) for v in (x.get(n), y.get(n), x.get(k), y.get(k))): return set()
    d = y[n] - x[n]
    return {k} if abs((y[k] - x[k]) - (d if n == 'Top Offset' else -d)) < 1e-6 else set()


def derived_echoes(src_buf, nb, ops):
    """ids of UNEDITED elements whose reader view changed only because the reader shows the edited element's parameter on them too (a view's Detail Level on its viewports / elevation arrows, a family's Section Shape on its
    symbols; QUEUE 64). Strict rule: the element changed in exactly ONE parameter, the edited parameter name, from exactly the edited element's old value to exactly its new value. Anything else stays an undeclared
    change and is refused by the gate. Numeric / string parameter edits only."""
    tg = [o for o in ops if o.get('op') in ('set_string', 'set_num') and o.get('param')]
    rn = [o for o in ops if o.get('op') == 'set_string' and o.get('field') == 'DBView.m_viewName']
    lvmv = [o for o in ops if o.get('op') == 'move' and o.get('dz') and not o.get('dx') and not o.get('dy')]      # pure vertical move: may be a Level elevation edit
    if not tg and not rn and not lvmv and not any(o.get('field') == 'DatumPlane.m_text' for o in ops): return []
    g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
    try: a, b = _read_params(src_buf), _read_params(nb)
    except Exception: return []
    edited = {o['eid'] for o in tg + rn + lvmv} | {o['eid'] for o in ops if o.get('op') == 'set_string' and o.get('field') == 'DatumPlane.m_text'}; out = set()
    for o in rn:      # view rename: dependents (Viewer, Viewport, Sheet) show the name under these keys; EVERY changed key must be one of them and go exactly old -> new
        x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); old, new = x.get('View Name'), y.get('View Name')
        if old is None or new is None or old == new: continue
        for e, d0 in a.items():
            if e in edited or e not in b: continue
            p0, p1 = g(d0), g(b[e]); ch = {k for k in set(p0) | set(p1) if p0.get(k) != p1.get(k)}
            if ch and ch <= _VIEWNAME_KEYS and all(p0.get(k) == old and p1.get(k) == new for k in ch): out.add(e)
    for o in [o for o in ops if o.get('op') == 'set_string' and o.get('field') == 'DatumPlane.m_text']:    # level rename: hosted elements show 'Level : <name>' under Work Plane / Host (strict: every changed key of the dependent is one of them and goes exactly 'Level : old' -> 'Level : new')
        x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); ck = {k: (x.get(k), y.get(k)) for k in set(x) | set(y) if x.get(k) != y.get(k)}
        pairs = {v for v in ck.values() if isinstance(v[0], str) and isinstance(v[1], str)}
        if len(pairs) != 1: continue
        old, new = next(iter(pairs))
        for e, d0 in a.items():
            if e in edited or e not in b: continue
            p0, p1 = g(d0), g(b[e]); ch = {k for k in set(p0) | set(p1) if p0.get(k) != p1.get(k)}
            if ch and ch <= _LEVELREF_KEYS and all(p0.get(k) == 'Level : ' + old and p1.get(k) == 'Level : ' + new for k in ch): out.add(e)
            elif ch and ch <= _LEVELNAME_KEYS and all(p0.get(k) == old and p1.get(k) == new for k in ch): out.add(e)
            elif ch and ch <= _LOCMARK_KEYS and all(isinstance(p0.get(k), str) and isinstance(p1.get(k), str) and _re.sub(r'(^|-)' + _re.escape(old) + r'(?=$|-|\()', lambda m: m.group(1) + new, p0[k]) == p1[k] != p0[k] for k in ch): out.add(e)      # grid rename: column location mark 'A(610)-W1(-17678)' carries the grid name before '('
    for o in lvmv:      # Level elevation +dz: instances placed on it keep their absolute Z, so the reader's 'Elevation from Level' falls by exactly dz (plus ~1e-14 rounding noise on two derived keys). Strict: ONLY those keys, that exact delta
        x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); dz = o['dz']
        if (a.get(o['eid']) or {}).get('class') != 'Level' or not isinstance(x.get('Elevation'), float) or not isinstance(y.get('Elevation'), float) or abs(y['Elevation'] - x['Elevation'] - dz) > 1e-6: continue
        for e, d0 in a.items():
            if e in edited or e not in b: continue
            p0, p1 = g(d0), g(b[e]); ch = {k for k in set(p0) | set(p1) if p0.get(k) != p1.get(k)}
            if not ch or 'Elevation from Level' not in ch or not ch <= _LEVELELEV_KEYS: continue
            v0, v1 = p0.get('Elevation from Level'), p1.get('Elevation from Level')
            if not (isinstance(v0, float) and isinstance(v1, float) and abs(v1 - v0 + dz) < 1e-6): continue
            if all(abs(p0.get(k) or 0) < 1e-9 and abs(p1.get(k) or 0) < 1e-9 for k in ch - {'Elevation from Level'}): out.add(e)
    for o in tg:
        n = o['param']; x, y = g(a.get(o['eid'])), g(b.get(o['eid']))
        if n not in x or n not in y or x[n] == y[n]: continue
        old, new = x[n], y[n]
        for e, d0 in a.items():
            if e in edited or e not in b: continue
            p0, p1 = g(d0), g(b[e])
            if p0 == p1: continue
            for m in (n,) + tuple(_ECHO_ALIAS.get(n, ())):      # a renamed view shows up as 'View Name' on its Viewer / Viewport elements
                ch = {k for k in set(p0) | set(p1) if p0.get(k) != p1.get(k)}
                if p0.get(m) == old and p1.get(m) == new and ch and ch <= {m, 'Type ' + m} and all(p0.get(k) == old and p1.get(k) == new for k in ch): out.add(e); break      # 'Type IfcGUID' is the same stored value shown under its type alias (SegmentCenterLine 1379375 of a duct has no parameter entries of its own; c4x-rvtmatrix 2026-11-02)
    return sorted(out)


_RB_MEMO = []


def _read_params(buf):
    """reader view (rvt_params.params) of the element parameters of these bytes, memoised for the last two buffers"""
    import hashlib, tempfile, shutil
    k = hashlib.sha256(buf).digest()
    for kk, v in _RB_MEMO:
        if kk == k: return v
    rr = os.path.expanduser('~/rvt-research')
    if rr not in sys.path: sys.path.insert(0, rr)
    import rvt_params
    v = _rp_disk_get(k)
    if v is None:
        d = tempfile.mkdtemp(prefix='rvtballet-rb-')
        try:
            f = os.path.join(d, 'x.rvt'); open(f, 'wb').write(buf); v = rvt_params.params(f)
        finally:
            shutil.rmtree(d, ignore_errors=True)
            g = sys.modules.get('rvt_geometry')      # its per-PATH caches (decoded records / docs) are never evicted and every read-back uses a fresh temp path: ~90 MB retained per save until the memory guard refused (found by c2x-rvtwrite2)
            if g is not None: getattr(g, '_ctx', {}).clear(); getattr(g, '_docs', {}).clear()
        _rp_disk_put(k, v)
    _RB_MEMO.insert(0, (k, v)); del _RB_MEMO[2:]
    return v


def _rp_file(key):
    d = _disk_dir()
    return os.path.join(d, 'rp-%s-%s.rpk' % (key.hex(), _reader_stamp())) if d else None


def _rp_disk_get(key):
    """reader params of the bytes with this sha256, cached on disk (checksummed, keyed by content hash AND reader code stamp); any damage is a miss"""
    import hashlib, pickle
    f = _rp_file(key)
    try:
        raw = open(f, 'rb').read()
        if len(raw) < 32 or hashlib.sha256(raw[32:]).digest() != raw[:32]: return None
        return pickle.loads(raw[32:])
    except Exception: return None


def _rp_disk_put(key, v, keep=6):
    import hashlib, pickle
    f = _rp_file(key)
    if not f: return
    try:
        os.makedirs(os.path.dirname(f), exist_ok=True); body = pickle.dumps(v, 4); t = f + '.%d.tmp' % os.getpid()
        with open(t, 'wb') as o: o.write(hashlib.sha256(body).digest() + body)
        os.replace(t, f); d = os.path.dirname(f)
        old = sorted((os.path.join(d, n) for n in os.listdir(d) if n.endswith('.rpk')), key=os.path.getmtime)
        for x in old[:-keep]: os.remove(x)
    except Exception: pass


def _same_mark_base(old, new):
    """a column location mark is 'GRID' or 'GRID(offset mm)'; a move changes only the offset ('D-1' -> 'D-1(610)', and 'W(137)-16(1162)' -> 'W(137)-16(1467)' when it already had one): same base text, different or added trailing offset"""
    import re
    new = str(new); strip = lambda t: re.sub(r'\(-?\d+(\.\d+)?\)$', '', t)
    return bool(old) and (new.startswith(old) or strip(old) == strip(new))      # 'D-1' -> 'D-1(610)', 'W-16(1162)' -> 'W-16(1467)', and 'D-1(610)' -> 'D-1' (moved back onto the grid line)


def _tris_of(buf, eid):
    """flat list of the triangle vertices (feet) of one FamilyInstance from the geometry reader, [] if none"""
    import sys, tempfile
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvt_geometry as G
    fd, tmp = tempfile.mkstemp(suffix='.rte')
    try:
        os.write(fd, buf); os.close(fd)
        r = G.element_geometry(tmp, eid)
        if not (isinstance(r, dict) and r.get('class') == 'FamilyInstance'): return []
        return [v for sl in r.get('solids', ()) if isinstance(sl, dict) for tr in sl.get('triangles', ()) for v in tr]
    finally:
        try: os.remove(tmp)
        except OSError: pass
        try: G._ctx.pop(tmp, None)
        except Exception: pass


def _rot_fit(a, b):
    """best-fit rotation about the vertical axis (degrees) taking vertex list a to b (translation removed), the largest xy residual and the largest z change"""
    import math
    ca = [sum(v[i] for v in a) / len(a) for i in (0, 1)]; cb = [sum(v[i] for v in b) / len(b) for i in (0, 1)]; sd = sc = 0.0
    for p, q in zip(a, b):
        x, y, u, w = p[0] - ca[0], p[1] - ca[1], q[0] - cb[0], q[1] - cb[1]; sd += x * u + y * w; sc += x * w - y * u
    th = math.atan2(sc, sd); c, sn = math.cos(th), math.sin(th)
    res = max(math.hypot(c * (p[0] - ca[0]) - sn * (p[1] - ca[1]) - (q[0] - cb[0]), sn * (p[0] - ca[0]) + c * (p[1] - ca[1]) - (q[1] - cb[1])) for p, q in zip(a, b))
    return math.degrees(th), res, max(abs(p[2] - q[2]) for p, q in zip(a, b))


def _inst_trf(buf, eid):
    """Trf.m_3x3 (9 doubles, row-major) of one element record read with the edit-lab record tracer, or None. For a FamilyInstance the columns are the instance axes in world coordinates: a rotation about the world vertical axis by t makes M_new = Rz(t) . M_old"""
    import sys, tempfile, struct
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvtedit
    d = tempfile.mkdtemp(prefix='rvtballet-trf-'); p = os.path.join(d, 'x.rvt')
    try:
        with open(p, 'wb') as f: f.write(buf)
        ed = rvtedit.Edit(p); log = ed.g.e.trace(eid)[3]
        for l in log:
            if l[1] == 'Trf.m_3x3' and l[3] - l[2] == 72: return struct.unpack_from('<9d', _own_body(ed, eid), l[2])
        return None
    finally:
        import shutil; shutil.rmtree(d, True)


def _is_rotation(m):
    """finite, orthonormal 3x3 (row-major 9-tuple), determinant +-1, tolerance 1e-6"""
    import math
    if not all(math.isfinite(x) and abs(x) <= 1.0 + 1e-6 for x in m): return False
    r = (m[0:3], m[3:6], m[6:9])
    return all(abs(sum(r[i][k] * r[j][k] for k in range(3)) - (1.0 if i == j else 0.0)) < 1e-6 for i in range(3) for j in range(3))


def _rotz_residual(m0, m1, deg):
    """largest entry of |M1 . M0^T - Rz(deg)| (M0 orthonormal, row-major 3x3 as 9-tuples)"""
    import math
    a = math.radians(deg); c, s = math.cos(a), math.sin(a); R = ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))
    A = [m1[0:3], m1[3:6], m1[6:9]]; B = [m0[0:3], m0[3:6], m0[6:9]]
    return max(abs(sum(A[i][k] * B[j][k] for k in range(3)) - R[i][j]) for i in range(3) for j in range(3))


def _bbox_class(buf, eid):
    """element class name from the geometry reader, '' if unknown"""
    import sys, tempfile
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvt_geometry as G
    fd, tmp = tempfile.mkstemp(suffix='.rte')
    try:
        os.write(fd, buf); os.close(fd)
        r = G.file_geometry_index(tmp); return str(r.get(eid, ''))
    finally:
        try: os.remove(tmp)
        except OSError: pass
        try: G._ctx.pop(tmp, None)
        except Exception: pass


def _own_body(ed, eid):
    """the element's own partition body (trace offsets index it; ed.g.bj is only the PART/first partition, c7x-rvtmove item 28)"""
    try: return ed.g.e.m.parts[ed.g.e.trace(eid)[0]]['joined']
    except Exception: return ed.g.bj


def _trf_origin(buf, eid, field='Trf.m_or'):
    """first Trf.m_or (3 finite doubles) of one element record read with the edit-lab record tracer, or None. For an SWall this is the placement origin: a move by (dx,dy,dz) adds exactly that (measured on the 2024 cols2 wall: (0,0,0) -> (1,2,0.5))"""
    import sys, tempfile, struct, math
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvtedit
    d = tempfile.mkdtemp(prefix='rvtballet-trf-'); p = os.path.join(d, 'x.rvt')
    try:
        with open(p, 'wb') as f: f.write(buf)
        ed = rvtedit.Edit(p)
        tr = ed.g.e.trace(eid)
        try: body = ed.g.e.m.parts[tr[0]]['joined']      # offsets are relative to the element's own partition (2020 files: ed.g.bj is another buffer and read garbage, c7x-rvtmove item 25)
        except Exception: body = ed.g.bj
        for l in tr[3]:
            if l[1] == field and l[3] - l[2] == 24:
                v = struct.unpack_from('<3d', body, l[2])
                return v if all(math.isfinite(x) and abs(x) < 1e7 for x in v) else None
        return None
    finally:
        import shutil; shutil.rmtree(d, True)


def _origin_field(src_buf, eid):
    """record field that witnesses a move of this class: TextNote carries TextElement.m_orig (no Trf)"""
    c = _bbox_class(src_buf, eid)
    return 'TextElement.m_orig' if c == 'TextNote' else 'Plane.m_origin' if c == 'Grid' else 'Trf.m_or'


def _origin_move_bad(src_buf, nb, o):
    """box not rebuilt by the writer: the record origin must shift by exactly the declared displacement (c2x-rvtsave: dx=7 bytes passed under declared dx=1). Returns a list of problems."""
    d = (o.get('dx', 0.0), o.get('dy', 0.0), o.get('dz', 0.0))
    try: fl_ = _origin_field(src_buf, o['eid']); w0 = _trf_origin(src_buf, o['eid'], fl_); w1 = _trf_origin(nb, o['eid'], fl_) if w0 else None
    except Exception: w0 = w1 = None
    if w0 is None or w1 is None: return ['moved element %d: box not rebuilt and no readable record origin, so the move cannot be verified (refused)' % o['eid']]
    if any(abs((w1[i] - w0[i]) - d[i]) > 1e-6 * max(1.0, abs(d[i])) + 1e-6 for i in range(3)): return ['moved element %d: record origin shifted by (%s), not the requested (%.4g, %.4g, %.4g)' % ((o['eid'], ', '.join('%.9g' % (w1[i] - w0[i]) for i in range(3))) + d)]
    return []

def _wall_line_origin(buf, eid):
    """first GLine.m_origin (3 finite doubles) of an SWall record = the wall's location line, or None. A wall move must shift it by exactly (dx,dy,dz): the placement Trf.m_or alone moves a cell pattern origin only (cols2 walls 301553-301556: the wall does not move, and 301556 then fails to open in Revit 2024, InsufficientResources)"""
    import sys, tempfile, struct, math
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvtedit
    d = tempfile.mkdtemp(prefix='rvtballet-gl-'); p = os.path.join(d, 'x.rvt')
    try:
        with open(p, 'wb') as f: f.write(buf)
        ed = rvtedit.Edit(p)
        for l in ed.g.e.trace(eid)[3]:
            if l[1] == 'GLine.m_origin' and l[3] - l[2] == 24:
                v = struct.unpack_from('<3d', _own_body(ed, eid), l[2])
                return v if all(math.isfinite(x) and abs(x) < 1e7 for x in v) else None
        return None
    finally:
        import shutil; shutil.rmtree(d, True)


def _bbox_of(buf, eid):
    """bounding box [[x0,y0,z0],[x1,y1,z1]] (feet) of one FamilyInstance read from bytes via the geometry reader, or None (other classes / no box)"""
    import sys, tempfile
    for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')):
        if lib not in sys.path: sys.path.insert(0, lib)
    import rvt_geometry as G
    fd, tmp = tempfile.mkstemp(suffix='.rte')
    try:
        os.write(fd, buf); os.close(fd)
        r = G.element_geometry(tmp, eid)
        bb = r.get('bbox') if isinstance(r, dict) and r.get('class') == 'FamilyInstance' else None      # only FamilyInstance boxes are exact translations: a wall's box carries join extensions that change with the move
        return [list(map(float, bb[0])), list(map(float, bb[1]))] if bb else None
    finally:
        try: os.remove(tmp)
        except OSError: pass
        try: G._ctx.pop(tmp, None)
        except Exception: pass


def _pair(fn, src_buf, nb, *a):
    """(value in the source, value in the output). A reader failure on the SOURCE means no witness (None, None); a failure on the OUTPUT keeps the source value and returns None for the output, so the caller refuses instead of skipping the check (fail-closed, e.g. a full disk truncating the temp copy)"""
    try: v0 = fn(src_buf, *a)
    except Exception: return None, None
    if not v0: return v0, None
    try: return v0, fn(nb, *a)
    except Exception: return v0, None


def _readback(src_buf, nb, ops):
    """the gate declares an edited element 'modified', so ANY change inside it passes verify. Read the edited elements back from the produced bytes: the edited parameter must hold the requested value (strings: exactly;
    numbers: changed), no other parameter of the element may change (except reader aliases carrying the new value) and the parameter count must not shrink. Severity-1 found by c3x-rvtmatrix: an emoji value left the
    element with 13 of 26 parameters and the gate said OK. A reader failure here refuses the save (nothing written)."""
    tg = [o for o in ops if o.get('op') in ('set_string', 'set_num') and o.get('param')]; mv = [o for o in ops if o.get('op') in ('move', 'rotate')]
    fl = [o for o in ops if o.get('op') == 'set_string' and not o.get('param')]   # field (name) edits: not visible as a parameter, so only presence and untouched parameters are checked
    dl = [o for o in ops if o.get('op') == 'delete']
    ct = [o for o in ops if o.get('op') == 'change_type']      # type changes: the instance must report the requested type id afterwards
    tn = [o for o in ops if o.get('op') == 'set_type_num']      # type parameter edits: the type must report the new value, every other type parameter unchanged
    if not tg and not mv and not fl and not dl and not ct and not tn: return
    g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
    sg = _import()
    try: a, b = _read_params(src_buf), _read_params(nb)
    except Exception as e: raise OutputUnreadable('the edited parameters could not be read back (%s: %s); nothing was written' % (type(e).__name__, e)) from e
    bad = []
    for o in tn:
        if o['eid'] not in b: bad.append('type %d missing in the output' % o['eid']); continue
        x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); nm = o.get('param')
        if len(y) < len(x): bad.append('type %d lost parameters (%d -> %d)' % (o['eid'], len(x), len(y)))
        if nm is not None:
            kk = nm if nm in y else (nm + '|Double' if nm + '|Double' in y else nm)      # type parameters are keyed 'Caption|Double' by the reader
            if not isinstance(y.get(kk), (int, float)) or abs(float(y[kk]) - o['value']) > 1e-9 * max(1.0, abs(o['value'])): bad.append('type %d: %s reads %r, not the requested %r' % (o['eid'], nm, y.get(kk), o['value']))
            for k in set(x) | set(y):
                if k != kk and x.get(k) != y.get(k): bad.append('type %d: untouched parameter %s changed (%r -> %r)' % (o['eid'], k, x.get(k), y.get(k)))
    for o in ct:
        if o['eid'] not in b: bad.append('type-changed element %d missing in the output' % o['eid']); continue
        x, y = g(a.get(o['eid'])), g(b.get(o['eid']))
        if str(y.get('Type Id')) != str(o['type_eid']): bad.append('type-changed element %d: Type Id is %s, not the requested %d' % (o['eid'], y.get('Type Id'), o['type_eid']))
        if len(y) < len(x): bad.append('type-changed element %d lost parameters (%d -> %d)' % (o['eid'], len(x), len(y)))
    for o in mv:      # a move changes placement only: the element must still be there with exactly its parameters
        if o['eid'] not in b: bad.append('moved element %d missing in the output' % o['eid'])
        else:
            x, y = g(a.get(o['eid'])), g(b.get(o['eid']))
            # the column location mark is derived from the position ('D-1' -> 'D-1(610)' = offset from grid D-1): a move legitimately appends the offset (seen on 2017 columns)
            own = {t['param'] for t in tg if t['eid'] == o['eid']}      # parameters a set op on the SAME element changes on purpose are verified by the set-op check below, not here
            lvl = o['op'] == 'move' and _bbox_class(src_buf, o['eid']) == 'Level'      # a level move changes exactly its Elevation, by dz (checked below)
            if lvl:
                e0, e1 = x.get('Elevation'), y.get('Elevation'); dz = o.get('dz', 0.0)
                if o.get('dx') or o.get('dy'): bad.append('moved level %d: only a vertical move (dz) is a level move' % o['eid'])
                elif not isinstance(e0, (int, float)) or not isinstance(e1, (int, float)) or abs((e1 - e0) - dz) > 1e-6 * max(1.0, abs(dz)) + 1e-6: bad.append('moved level %d: Elevation %r -> %r, not the requested shift of %.6g ft' % (o['eid'], e0, e1, dz))
            ch = [k for k in set(x) | set(y) if k not in own and not (lvl and k == 'Elevation') and x.get(k) != y.get(k) and not (k.startswith('Column Location Mark') and isinstance(x.get(k), str) and _same_mark_base(x[k], y.get(k)))]
            if ch: bad.append('moved element %d: parameters changed' % o['eid'])
            if o['op'] == 'move' and not any(r.get('op') == 'rotate' and r['eid'] == o['eid'] for r in mv):      # the displacement itself: the element's bounding box must shift by exactly (dx, dy, dz) (feet); skipped only when the geometry reader has no box for the SOURCE element
                b0, b1 = _pair(_bbox_of, src_buf, nb, o['eid'])
                if b0 is not None:
                    d = (o['dx'], o['dy'], o['dz'])
                    if b1 is None: bad.append('moved element %d: no geometry in the output' % o['eid'])
                    elif b1 == b0 and nb != src_buf: bad.extend(_origin_move_bad(src_buf, nb, o))      # box unchanged but the output differs from the source: the cached tessellation of some elements (HVAC duct 1365188) is not rebuilt by the writer although Revit moves the element exactly (+2 ft, API readback); not a witness. Byte-identical output is still refused below
                    elif any(abs((b1[i][k] - b0[i][k]) - d[k]) > 1e-6 * max(1.0, abs(d[k])) + 1e-6 for i in (0, 1) for k in range(3)): bad.append('moved element %d: displacement in the output is not the requested (%.4g, %.4g, %.4g); measured box shift (%s)' % ((o['eid'],) + d + (' | '.join(', '.join('%.9g' % (b1[i][k] - b0[i][k]) for k in range(3)) for i in (0, 1)),)))
    for o in [r for r in mv if r['op'] == 'move']:      # no witness, no move: only classes whose displacement the gate can measure (instance box or record origin; wall / dimension origin below) are accepted. SketchPlane and GeoLocation moves used to pass on 'bytes differ' alone (c6x-rvtmatrix 2026-11-04; a project-location shift nobody can read back)
        if any(r.get('op') == 'rotate' and r['eid'] == o['eid'] for r in mv): continue
        try: cl = _bbox_class(src_buf, o['eid'])
        except Exception: cl = ''
        if cl and cl not in ('FamilyInstance', 'SWall', 'LinearDimString', 'RvtLinkInstance', 'TextNote', 'Level', 'Grid'): bad.append('moved element %d: class %s has no readable displacement witness, so the move cannot be verified (refused)' % (o['eid'], cl))
        elif cl in ('FamilyInstance', ''):      # '' = the class index does not list the element (older files): box or record origin must witness
            try: has_box = _bbox_of(src_buf, o['eid']) is not None
            except Exception: has_box = False
            if not has_box:
                w0, w1 = _pair(_trf_origin, src_buf, nb, o['eid'])
                d = (o.get('dx', 0.0), o.get('dy', 0.0), o.get('dz', 0.0))
                if w0 is None or w1 is None or any(abs((w1[i] - w0[i]) - d[i]) > 1e-6 * max(1.0, abs(d[i])) + 1e-6 for i in range(3)): bad.append('moved element %d: no box and no readable record origin shift, so the move cannot be verified (refused)' % o['eid'])
    for o in [r for r in mv if r['op'] == 'rotate']:      # the rotation itself: the element's mesh must be turned by exactly o['deg'] about the vertical axis (rigid, z unchanged); FamilyInstance only, skipped when the geometry reader has no mesh for the SOURCE element
        try: t0 = _tris_of(src_buf, o['eid']); t1 = _tris_of(nb, o['eid']) if t0 else None
        except Exception: t0, t1 = None, None
        q0, q1 = _pair(_inst_trf, src_buf, nb, o['eid'])
        if q0 is not None and not _is_rotation(q0): q0 = None      # the tracer did not land on a real orientation matrix in this file (garbage / NaN / scaled): no witness
        w0, w1 = _pair(_trf_origin, src_buf, nb, o['eid'])
        if w0 is not None and w1 is None: bad.append('rotated element %d: the instance origin could not be read from the output, so the rotation cannot be verified (refused)' % o['eid'])
        if w0 is not None and w1 is not None:      # rotation is about the instance origin: the origin must shift by exactly the declared moves of this element (none = zero); a hidden translation passed the mesh fit (c2x-rvtmove, tests/test_save_move_then_rotate.py)
            dd = [sum(m.get(k, 0.0) for m in mv if m['op'] == 'move' and m['eid'] == o['eid']) for k in ('dx', 'dy', 'dz')]
            if any(abs((w1[i] - w0[i]) - dd[i]) > 1e-6 * max(1.0, abs(dd[i])) + 1e-6 for i in range(3)): bad.append('rotated element %d: the instance origin moved by (%.4g, %.4g, %.4g) ft, declared (%.4g, %.4g, %.4g)' % ((o['eid'],) + tuple(w1[i] - w0[i] for i in range(3)) + tuple(dd))); continue
        if q0 is not None:      # the record's own orientation matrix: independent of what the geometry reader can show
            if q1 is None or _rotz_residual(q0, q1, o['deg']) > 1e-6: bad.append('rotated element %d: the orientation matrix in the output is not the source turned by %.4g deg about the vertical axis' % (o['eid'], o['deg'])); continue
        if not t0: continue
        if not t1 or len(t1) != len(t0): continue      # the reader returns a DIFFERENT mesh for the output (2019/2022 sample instances: type geometry in local coordinates once the saved tessellation is dropped, 1368 -> 1239 vertices): no witness, not a failure (measured by tools/rvtrot_years.py); equal-count meshes are always compared
        if t1 == t0 and nb != src_buf: continue      # cached tessellation not rebuilt (same exemption as moves); byte-identical output is refused below
        import math
        th, res, dz = _rot_fit(t0, t1); err = abs(math.remainder(th - o['deg'], 360.0))
        if err > 1e-3 or res > 1e-4 or dz > 1e-5: bad.append('rotated element %d: the output is turned by %.4g deg (residual %.2g ft, dz %.2g), not the requested %.4g' % (o['eid'], th, res, dz, o['deg']))
    for o in [r for r in mv if r['op'] == 'move']:      # walls and linear dimensions: the placement origin in the record must move by exactly the requested displacement (the geometry reader has no mesh for a moved wall, and the box carries join extensions)
        if any(r.get('op') == 'rotate' and r['eid'] == o['eid'] for r in mv): continue
        try:
            if _bbox_class(src_buf, o['eid']) not in ('SWall', 'LinearDimString', 'RvtLinkInstance', 'TextNote', 'Grid'): continue
            fl_ = _origin_field(src_buf, o['eid'])
        except Exception: fl_ = False
        w0, w1 = _pair(_trf_origin, src_buf, nb, o['eid'], fl_) if fl_ is not False else (None, None)
        d = (o['dx'], o['dy'], o['dz'])
        if w0 is None and _bbox_class(src_buf, o['eid']) == 'RvtLinkInstance': bad.append('moved Revit link instance %d: no readable record origin (Trf.m_or), so the move cannot be verified (refused)' % o['eid']); continue
        if _bbox_class(src_buf, o['eid']) == 'SWall':      # the location line itself must move (the Trf origin alone is not a wall move)
            g0, g1 = _pair(_wall_line_origin, src_buf, nb, o['eid'])
            if g0 is not None and (g1 is None or any(abs((g1[i] - g0[i]) - d[i]) > 1e-6 * max(1.0, abs(d[i])) + 1e-6 for i in range(3))): bad.append('moved wall %d: the wall location line in the output is not the source moved by (%.4g, %.4g, %.4g) (only a pattern origin moved)' % ((o['eid'],) + d)); continue
        if w0 is None and _bbox_class(src_buf, o['eid']) == 'TextNote': bad.append('moved text note %d: no readable TextElement.m_orig, so the move cannot be verified (refused)' % o['eid']); continue
        if w0 is None: continue
        if w1 is None or any(abs((w1[i] - w0[i]) - d[i]) > 1e-6 * max(1.0, abs(d[i])) + 1e-6 for i in range(3)): bad.append('moved element %d: the placement origin in the output is not the source moved by (%.4g, %.4g, %.4g)' % ((o['eid'],) + d))
    for o in dl:      # a declared deletion must really have happened: the gate accepts a manifest that names a still-present element as deleted (tests/test_save_escape_delete.py)
        if o['eid'] in a and o['eid'] in b: bad.append('element %d was declared deleted but is still in the output' % o['eid'])
    if dl:      # a delete must not touch the elements that survive: every element present before and after reads back with identical parameters (measured 0 drift: 2024 Construction wall delete)
        _drift = [e for e in a if e in b and g(a[e]) != g(b[e])]
        if _drift: bad.append('delete changed the parameters of %d surviving element(s) (e.g. %s)' % (len(_drift), ', '.join(str(e) for e in _drift[:3])))
    for o in fl:
        if o['eid'] not in b: bad.append('field-edited element %d missing in the output' % o['eid'])
        else:
            x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); ch = [k for k in set(x) | set(y) if x.get(k) != y.get(k) and y.get(k) != o['value']]   # reader aliases (e.g. Type Name) may carry the new name
            if ch: bad.append('field-edited element %d: parameters changed (%s)' % (o['eid'], ', '.join('%s: %r -> %r' % (k, str(x.get(k))[:20], str(y.get(k))[:20]) for k in sorted(ch))[:200]))
    for o in tg:
        x, y = g(a.get(o['eid'])), g(b.get(o['eid'])); n = o['param']
        if o['eid'] not in b: bad.append('element %d missing in the output' % o['eid']); continue
        if len(y) < len(x): bad.append('element %d lost parameters (%d -> %d)' % (o['eid'], len(x), len(y))); continue
        ch = {k for k in set(x) | set(y) if x.get(k) != y.get(k)}
        if n not in ch and not (n in x and x[n] == o['value']): bad.append('element %d: parameter %r unchanged by the edit' % (o['eid'], n))
        if o['op'] == 'set_string' and y.get(n) != o['value']: bad.append('element %d: %r reads back %r, not the requested value' % (o['eid'], n, str(y.get(n))[:30]))
        if o['op'] == 'set_num' and isinstance(y.get(n), (int, float)) and isinstance(o.get('value'), (int, float)) and abs(float(y[n]) - float(o['value'])) > 1e-6 * max(1.0, abs(float(o['value']))):      # severity: a wrong NUMBER inside the declared element used to pass (c1x-rvtmatrix 2026-11-02)
            bad.append('element %d: %r reads back %r, not the requested %r' % (o['eid'], n, y.get(n), o['value']))
        sib = {q.get('param') for q in tg if q['eid'] == o['eid'] and q is not o}      # parameters the same save edits on this element: each is verified by its own iteration, so they are not 'other' changes (c6x-rvtmatrix item 8)
        _d = _offset_echo(n, x, y)      # Top/Base Offset: the reader's derived 'Unconnected Height|Double' moves by exactly the offset delta (Revit-verified readback of the same quantity)
        if [k for k in ch - {n} - sib - _d if y.get(k) != y.get(n)]: bad.append('element %d: %d other parameter(s) changed (%s)' % (o['eid'], len(ch - {n} - sib), ', '.join('%s: %s -> %s' % (k, str(x.get(k))[:12], str(y.get(k))[:12]) for k in sorted(ch - {n} - sib, key=str)[:4])))
    if bad: raise sg.VerifyFailed('read-back of the edited element(s) failed: %s' % '; '.join(bad[:3]), {'n_unexpected': len(bad), 'unexpected': bad[:20]})


def _cloud_gate(*paths):
    from . import plat
    for f in paths:
        if f and plat.fsio.is_cloud_placeholder(f):
            raise CloudPlaceholder('the file is an online-only cloud placeholder (OneDrive/Dropbox) that is not downloaded yet; make it available offline first, then retry (nothing written): ' + f)


def risky_membership(mem, ops):
    """keep group / design-option reasons always; 'hosted on N' only for move/rotate ops on that element (a parameter edit of a hosted element does not change where it sits)"""
    moved = {o['eid'] for o in ops if o.get('op') in ('move', 'rotate')}; out = {}
    for e, why in mem.items():
        w = [x for x in why if not x.startswith(('hosted on ', 'hosts ', 'dimensioned by ', 'level constrains ')) or e in moved]
        if w: out[e] = w
    return out


def group_warning(ss, mid, buf):
    """warning text when a pending edit touches a group member / group instance / design-option element (None otherwise). Revit evidence (rac_advanced 2024, in-place move of one array-group member): the file opens, audits and regenerates cleanly, but that instance no longer matches the other 15 instances of its group type, so the copy is not what the user meant."""
    from .edit import compose
    ops = compose(list(ss.edits(mid).ops))      # what is really applied (a move +2 / -2 that cancels is not a move)
    if not ops: return None
    try: mem = risky_membership(membership(buf, {o['eid'] for o in ops}), ops)
    except Exception as e: return 'could not check whether the edited elements belong to a group or design option (%s): verify the copy in Revit' % e
    if not mem: return None
    e0 = sorted(mem)[0]
    return 'element %d is part of a group or design option, or is a moved element with dependents (hosted doors/windows, dimensions, level-relative elements) (%s): Revit opens such a copy without complaint, but a group member then differs from the other instances of its group type, a moved window/door can end up off its host wall, and dimensions or level-relative elements are not updated; check the copy in Revit before relying on it' % (e0, '; '.join(mem[e0]))


def save_as(ss, mid, src, dest, overwrite=False, new_bytes=None, manifest=None):
    """SAVE AS: never touches the source. new_bytes defaults to the loaded bytes (identity save)."""
    _cloud_gate(src, dest); ss.progress.pop(mid, None); _stage(ss, mid, 'applying edits'); d = ss.doc(mid, src); d.adapter.report = lambda t: _stage(ss, mid, t); _refuse_damaged(d)
    check_memory(src, d.buf)      # TooBig (507) before any work; the UI then offers the labelled limited verification
    gw = group_warning(ss, mid, d.buf) if new_bytes is None else None
    explicit = new_bytes is not None
    new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest); _refuse_bad_output(new_bytes); _stage(ss, mid, 'verifying and writing')
    exp = [] if explicit else expectations(ss.edits(mid).ops, [int(k[3:]) for k in manifest.get('deleted', ())])
    r = result_json(_guard(_import().save_as, d, new_bytes, dest, manifest, overwrite=overwrite))
    if exp: r['expectations'] = exp      # replayable by tools/rvt_expect_check.py through the Revit API
    if gw: r.setdefault('warnings', []).append(gw)
    lc = layout_changes(d.buf, new_bytes) if new_bytes is not d.buf else []
    if lc is None: r.setdefault('warnings', []).append('the page-layout check could not run: this output is NOT confirmed to keep the layout of the source')
    elif lc: r.setdefault('warnings', []).extend('page layout of %s changed (%s -> %s, %+d bytes): this layout is NOT confirmed to open in Revit; verify the copy in Revit before relying on it' % (k, la, lb, dz) for k, la, lb, dz in lc)
    _note_derived(ss, mid, r)
    return r


def save_as_light(ss, mid, src, dest, overwrite=False):
    """SAVE AS with LIMITED verification (rvtballet.lightverify) for models too large for the element-level verify. Explicit opt-in, SAVE AS only: never used for overwrite."""
    from .lightverify import light_verify
    _cloud_gate(src, dest); ss.progress.pop(mid, None); _stage(ss, mid, 'applying edits'); d = ss.doc(mid, src, precheck=False); _refuse_damaged(d)
    new_bytes, manifest = _pending(ss, mid, d, None, None, light=True); _refuse_bad_output(new_bytes); n = len(ss.edits(mid).ops)
    _stage(ss, mid, 'limited verification (structure only)'); rep = light_verify(d.buf, new_bytes, max(1, n))
    _stage(ss, mid, 'writing'); r = result_json(_guard(_import().save_as, d, new_bytes, dest, manifest, overwrite=overwrite, verify=False))
    r['verify'] = rep; r['limited_verification'] = True
    lc = layout_changes(d.buf, new_bytes)
    lw = ['the page-layout check could not run: this output is NOT confirmed to keep the layout of the source'] if lc is None else ['page layout of %s changed (%s -> %s, %+d bytes): NOT confirmed to open in Revit' % (k, la, lb, dz) for k, la, lb, dz in (lc or [])]
    r['warnings'] = r.get('warnings', []) + lw + ['LIMITED verification only (no element-level comparison): the output is structurally consistent with the source (all untouched streams identical, only %d gzip member(s) of the edited partition changed) but it is NOT confirmed that only the declared elements changed or that Revit accepts it. Open the copy in Revit before relying on it.' % rep['changed_members']]
    return r


def save_overwrite(ss, mid, src, force=False, new_bytes=None, manifest=None):
    """SAVE! : overwrite the source (needs allow_overwrite + open gate; Conflict if the file changed since load unless force)"""
    _cloud_gate(src); _network_gate(src); ss.progress.pop(mid, None); _stage(ss, mid, 'applying edits'); d = ss.doc(mid, src); d.adapter.report = lambda t: _stage(ss, mid, t); _refuse_damaged(d)
    check_memory(src, d.buf)
    if os.path.islink(d.path): d.path = os.path.realpath(d.path)      # SAVE! of a symlinked source must replace the real file and keep the link (savegate replaces the link itself otherwise)
    ws = worksharing_state(d.buf)
    if not (ws or '').startswith('Not enabled') and os.environ.get('RVTBALLET_ALLOW_WORKSHARED') != '1':
        raise Workshared('overwrite refused: the model is %s (Worksharing: %s); worksets and the central link are not maintained by the writer. Use SAVE AS and check the copy in Revit; the file was not touched.' % ('workshared' if ws else 'of unknown worksharing state', ws or 'unreadable'))
    from .edit import compose
    ops = compose(list(ss.edits(mid).ops)) if new_bytes is None else []
    if ops and os.environ.get('RVTBALLET_ALLOW_GROUP_EDIT') != '1':
        _stage(ss, mid, 'checking groups and design options')
        try: mem = risky_membership(membership(d.buf, {o['eid'] for o in ops}), ops)
        except OSError as e: raise DiskError('overwrite refused: disk error while checking the edited elements (%s); the file was not touched. Free disk space or use SAVE AS elsewhere.' % e)
        except Exception as e: raise GroupOrOption('overwrite refused: could not check whether the edited elements belong to a group or design option (%s); the file was not touched. Use SAVE AS.' % e)
        if mem:
            e0 = sorted(mem)[0]
            raise GroupOrOption('overwrite refused: element %d is part of a group or design option, or is a moved element with dependents (hosted elements, dimensions, level-relative elements) (%s); such edits can leave an inconsistent model that Revit still opens. Use SAVE AS and check the copy; the file was not touched.' % (e0, '; '.join(mem[e0])))
    new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest); _refuse_bad_output(new_bytes); _stage(ss, mid, 'verifying and writing')
    lc = layout_changes(d.buf, new_bytes) if new_bytes is not d.buf else []
    if lc is None and os.environ.get('RVTBALLET_ALLOW_LAYOUT_CHANGE') != '1': raise LayoutChanged('overwrite refused: the page-layout check could not run, so the output is not known to keep the source layout. Use SAVE AS (override: RVTBALLET_ALLOW_LAYOUT_CHANGE=1).')
    if lc and os.environ.get('RVTBALLET_ALLOW_LAYOUT_CHANGE') != '1':
        raise LayoutChanged('overwrite refused: the page layout of %s would change (%s -> %s, %+d bytes) and this is not confirmed to open in Revit. Use SAVE AS and check the copy (override: RVTBALLET_ALLOW_LAYOUT_CHANGE=1).' % (lc[0][0], lc[0][1], lc[0][2], lc[0][3]))
    try: nlink = os.stat(d.path).st_nlink
    except OSError: nlink = 1
    r = result_json(_guard(_import().save, d, new_bytes, manifest, force=force))
    _note_derived(ss, mid, r)
    if nlink > 1: r.setdefault('warnings', []).append('the file had %d hard links: the save replaced this name only, the other name(s) still hold the OLD content' % nlink)
    del ss.edits(mid).ops[:ss.applied.pop(mid, 0)]          # only the ops that were applied are in the file now
    if not ss.edits(mid).ops:
        from . import editstore; editstore.sync(src, [], None)      # nothing pending any more: the stored copy goes
    return r


def backups(src):
    sg = _import()
    import time
    src = os.path.realpath(src)      # backups of a symlinked source are made for the real file
    return [{'n': i, 'name': n, 'path': p, 'size': sz, 'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(p).st_mtime))}
            for i, (n, p, sz) in enumerate(sg.list_backups(src))]


def restore_backup(ss, mid, src, n=0):
    """put backup n (0 = newest) back over the source (savegate backs the current file up first); the doc is re-opened so the fingerprint matches"""
    sg = _import(); ss.close(mid); ops = ss.edits(mid).ops; kept = list(ops); src = os.path.realpath(src)      # a symlinked source is restored in its real file
    try: used = sg.restore(src, n)
    except BaseException:
        ops[:] = kept; raise           # a refused restore (corrupt/missing backup, lock) left the file as it was: the user's pending edits stay too
    ops.clear()                        # pending edits were recorded against the old content: only a restore that happened drops them
    from . import editstore; editstore.sync(src, [], None)
    from savegate.atomic import sha256_file
    return {'ok': True, 'restored_from': used, 'sha256': sha256_file(src)[:12], 'size': os.path.getsize(src)}


def recoverable(ss):
    """edit journals of sessions that never closed (crash / kill), excluding this server's own live sessions"""
    sg = _import(); live = {d.journal.path for d in ss.docs.values() if d.journal}
    out = []
    for p, ents in sg.recover():
        if p in live: continue
        src = next((e.get('source') for e in ents if e.get('kind') == 'open'), None)
        out.append({'journal': p, 'source': src, 'entries': len(ents), 'last': ents[-1].get('kind'), 'stage': ents[-1].get('stage') or ents[-1].get('kind')})
    return out


def sync_edits(ss, mid, src):
    """persist the pending edit list (see editstore); called after every change of it"""
    from . import editstore
    d = ss.docs.get(mid)
    sha = d.fingerprint.sha256 if d is not None and getattr(d, 'fingerprint', None) else None
    if sha is None and ss.edits(mid).ops: return             # no loaded document = no fingerprint to bind the ops to: do not store unbound ops
    editstore.sync(src, ss.edits(mid).ops, sha)


def recover_edits(ss, mid, src):
    """replay the stored ops of this file through add_edit (trial replay each); all or nothing"""
    from . import editstore
    d = ss.doc(mid, src); ops, why = editstore.load(src, d.fingerprint.sha256)
    if why: raise StaleEdits(why)
    if not ops: return {'ok': True, 'n': len(ss.edits(mid).ops), 'recovered': 0}
    e = ss.edits(mid); before = list(e.ops)
    try:
        add_edits(ss, mid, src, ops)
    except BaseException:
        e.ops[:] = before; sync_edits(ss, mid, src); raise
    return {'ok': True, 'n': len(e.ops), 'recovered': len(ops)}


def _refuse_dim_moves(buf, ops):
    """a LinearDimString move changes the record origin (the gate sees it) but Revit 2024 reads identical dimension segment origins afterwards (c2x-rvtmatrix, Snowdon Plumbing VM): the viewer must not promise it"""
    from .edit import EditError
    for o in ops:
        if o.get('op') == 'move':
            try: cl = _bbox_class(buf, o['eid'])
            except Exception: cl = ''
            if cl == 'LinearDimString': raise EditError('element %d is a dimension: Revit does not honour a moved dimension record, so the move is refused' % o['eid'])


def add_edit(ss, mid, src, op):
    """record an edit after a trial replay on the loaded bytes (so an op the writer cannot apply is refused now, not at save time)"""
    from .edit import apply_full, validate_op
    op = validate_op(op)
    try: d = ss.doc(mid, src); _refuse_dim_moves(d.buf, [op]); e = ss.edits(mid); _, deleted = apply_full(d.buf, e.ops + [op])
    except ValueError as ex:      # the reader's own refusal of a damaged file ('file truncated: ...'): a clean 409, not a bare 500
        if 'truncated' in str(ex).lower() or 'corrupt' in str(ex).lower(): raise SourceDamaged('the model file is damaged (%s); nothing was written' % str(ex)[:160])
        raise
    e.ops.append(op); sync_edits(ss, mid, src)
    return {'ok': True, 'n': len(e.ops), 'ops': e.ops, 'manifest': e.manifest(deleted)}


def add_edits(ss, mid, src, ops):
    """record several edits after ONE trial replay of the whole list (add_edit replays everything per call: about 20 s each on a 28 MB model). All or none: a refusal of any op leaves the recorded edits as they were."""
    from .edit import apply_full, validate_op
    ops = [validate_op(o) for o in ops]
    try: d = ss.doc(mid, src); _refuse_dim_moves(d.buf, ops); e = ss.edits(mid); _, deleted = apply_full(d.buf, e.ops + ops)
    except ValueError as ex:
        if 'truncated' in str(ex).lower() or 'corrupt' in str(ex).lower(): raise SourceDamaged('the model file is damaged (%s); nothing was written' % str(ex)[:160])
        raise
    e.ops.extend(ops); sync_edits(ss, mid, src)
    return {'ok': True, 'n': len(e.ops), 'ops': e.ops, 'manifest': e.manifest(deleted)}


class BadDest(Exception): pass


class StaleEdits(Exception): pass


def check_dest(dest, src):
    """SAVE AS destination sanity, before anything is read or verified. Raises BadDest."""
    if not isinstance(dest, str) or not dest.strip(): raise BadDest('destination path required')
    if '\0' in dest or len(dest) > 4096: raise BadDest('destination path is invalid (NUL or too long)')
    if not os.path.isabs(dest): raise BadDest('destination must be an absolute path')
    if os.path.basename(dest) in ('', '.', '..') or dest.endswith(('/', os.sep)): raise BadDest('destination must name a file')
    if os.path.realpath(dest) != os.path.realpath(src) and os.path.splitext(dest)[1].lower() not in ('.rvt', '.rte', '.rfa', '.rft'): raise BadDest('destination must end in .rvt, .rte, .rfa or .rft')
    _fam = lambda e: e in ('.rfa', '.rft')      # a project saved under a family extension (or the reverse) is a mislabeled file Revit may flag on open
    if _fam(os.path.splitext(src)[1].lower()) != _fam(os.path.splitext(dest)[1].lower()): raise BadDest('destination extension must stay in the same kind as the source (project .rvt/.rte, family .rfa/.rft)')
    from . import plat
    _bn = plat.fsio.bad_filename(os.path.basename(dest))
    if _bn: raise BadDest(_bn)
    d = os.path.dirname(dest)
    if not os.path.isdir(d): raise BadDest('destination folder does not exist: %s' % d)
    if os.path.lexists(dest) and not os.path.isfile(dest) and not os.path.islink(dest): raise BadDest('destination exists and is not a regular file')
    same = os.path.normcase(os.path.realpath(dest)) == os.path.normcase(os.path.realpath(src))
    try: same = same or (os.path.exists(dest) and os.path.samefile(dest, src))      # case-insensitive filesystems, hard links
    except OSError: pass
    if same: raise BadDest('destination is the source file (use SAVE to overwrite)')
    return dest


class NetworkFS(Exception):
    """SAVE! source is on a network share or FUSE mount: rename/flush are not atomic there and sync clients may upload a half-written file"""


def _network_gate(path):
    from . import plat
    k = plat.fsio.network_fs_kind(path)
    if k and os.environ.get('RVTBALLET_ALLOW_NETWORK_OVERWRITE') != '1':
        raise NetworkFS('the model is on a network or FUSE file system (%s): rename and flush are not atomic there, so SAVE! is refused and the file was not touched. Use SAVE AS to a local folder, or set RVTBALLET_ALLOW_NETWORK_OVERWRITE=1 if you accept that risk' % k)


class CloudPlaceholder(Exception):
    """source or destination is an online-only OneDrive/Dropbox file"""


class LayoutChanged(Exception):
    """overwrite refused: the page layout of a stream differs from the source (not confirmed to open in Revit)"""


def layout_changes(src_bytes, out_bytes):
    """streams whose page layout (full pages, last-page capacity) or size differs: [(stream, (full, cap_last) src -> out, size delta)]. Returns None when the check could not run (write-lab modules missing / parse error): callers must treat None as UNKNOWN, never as clean."""
    try:
        from .edit import WL
        if WL not in sys.path: sys.path.insert(0, WL)
        import cfb, rvtw
        a = cfb.CFB(src_bytes).streams(); b = cfb.CFB(out_bytes).streams(); out = []
        for k in a:
            if k not in b or a[k].data == b[k].data or not k.startswith('Partitions/'): continue
            sa, sb = rvtw.Stream(a[k].data), rvtw.Stream(b[k].data)
            la, lb = (sa.full, getattr(sa, 'cap_last', None)), (sb.full, getattr(sb, 'cap_last', None))
            if la != lb or len(a[k].data) != len(b[k].data): out.append((k, la, lb, len(b[k].data) - len(a[k].data)))
        return out
    except Exception:
        return None
