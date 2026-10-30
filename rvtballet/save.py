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

def _cached_adapter():
    """RvtAdapter whose snapshot() is memoised by content hash (last 3 buffers): the source dump (~14 s on a 5.6k-element file) is taken once per loaded
    file instead of at every save; the output of a save is cached too, so after SAVE (overwrite) the new loaded bytes cost nothing."""
    import hashlib
    from savegate.adapters import RvtAdapter
    class CachedRvtAdapter(RvtAdapter):
        def __init__(self, *a, **k): super().__init__(*a, **k); self._memo = []; self.report = lambda stage: None
        def snapshot(self, buf):
            key = hashlib.sha256(buf).digest()
            for k, snap, keys in self._memo:
                if k == key: self._keys = set(keys); return dict(snap)
            self.report('reading %d MB (element dump for verification)' % (len(buf) >> 20))
            snap = super().snapshot(buf); self._memo = ([(key, dict(snap), set(self._keys))] + self._memo)[:3]
            return snap
    return CachedRvtAdapter


class TooBig(Exception):
    """not enough memory budget to hold source + output + snapshots (measured ~8x the file size)"""


def element_rows(path):
    """decompressed Global/ElemTable bytes / 28 = rough element count (cheap: one stream); None when the write-lab modules are unavailable or the file cannot be parsed"""
    try:
        from .edit import WL
        if WL not in sys.path: sys.path.insert(0, WL)
        import cfb, rvtw
        with open(path, 'rb') as f: P = bytes(rvtw.Stream(cfb.CFB(f.read()).streams()['Global/ElemTable'].data).payload)
        return sum(r for (_, _, r) in rvtw.members(P, P.find(rvtw.GZ))) // 28
    except Exception:
        return None


def check_memory(path):
    """refuse BEFORE opening when the element-level verify would not fit: need = max(9 x file size, KB-per-row x element rows). Measured on real 2024 projects: a 24 MB file with ~26k rows used ~4.5 GB+
    (~170 KB/row) while a padded 305 MB container with 5.6k rows used 2.4 GB: memory follows element count / geometry, not file size. 200 KB/row is deliberately conservative (refusing is safe, running out of memory is not)."""
    from ._vendor.rvtplat import mem
    size = os.path.getsize(path); need = size * float(os.environ.get('RVTBALLET_SAVE_MEM_FACTOR', '9')); rows = element_rows(path)
    if rows: need = max(need, rows * float(os.environ.get('RVTBALLET_SAVE_MEM_PER_ROW_KB', '200')) * 1024)
    budget = mem.limit_gb(0.7) * 2 ** 30 - mem.rss_bytes()
    if need > budget:
        raise TooBig('saving this %.0f MB file (about %s elements) needs roughly %.1f GB of memory but only %.1f GB is available to the viewer (raise RVTPLAT_MEM_GB or close other programs)'
                     % (size / 2 ** 20, '%d' % rows if rows else '?', need / 2 ** 30, max(budget, 0) / 2 ** 30))


class SaveSessions:
    """one savegate Doc per model id, opened lazily from the source .rvt (fingerprint taken at first use = load time)"""
    def __init__(self, cfg=None):
        self.docs = {}; self.ed = {}; self.busy = set(); self.progress = {}; self.applied = {}; import threading; self._lk = threading.RLock(); self._cfg = cfg
    @property
    def cfg(self):
        """Config(allow_overwrite from env RVTBALLET_ALLOW_OVERWRITE=1; the oracle gate stays on)"""
        if self._cfg is not None: return self._cfg
        sg = _import()
        return sg.Config(allow_overwrite=os.environ.get('RVTBALLET_ALLOW_OVERWRITE') == '1') if sg else None
    @property
    def available(self): return _import() is not None
    def doc(self, mid, src):
        with self._lk: return self._doc(mid, src)
    def _doc(self, mid, src):
        sg = _import()
        if sg is None: raise RuntimeError('savegate is not installed')
        d = self.docs.get(mid)
        if d is None or d.path != os.path.abspath(src):
            check_memory(src)
            if d is not None: d.close(); self.docs.pop(mid, None)       # replaced: do not leak its journal
            from savegate import rvt_elements
            d = sg.open_doc(src, _cached_adapter()(elements_fn=rvt_elements.elements), cfg=self.cfg)      # element-level verify
            if d.version == '?':          # an explicit adapter skips pick_adapter's refusal of non-Revit bytes
                d.close(); raise sg.UnsupportedVersion('%s is not a Revit file (unknown format, nothing can be saved)' % os.path.basename(src))
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


class OutputUnreadable(Exception):
    """the reader crashed while re-reading the produced bytes: the output is not trustworthy, nothing was written"""


def _guard(fn, *a, **k):
    sg = _import()
    try: return fn(*a, **k)
    except (sg.SaveError, OSError): raise
    except Exception as e:
        raise OutputUnreadable('the edited file could not be read back (%s: %s); nothing was written' % (type(e).__name__, e)) from e


def error_status(exc):
    """savegate exception -> (http status, machine code)"""
    n = type(exc).__name__
    return {'Conflict': (409, 'conflict'), 'GateClosed': (409, 'gate_closed'), 'OverwriteDisabled': (409, 'overwrite_disabled'),
            'Exists': (409, 'exists'), 'Locked': (423, 'locked'), 'VerifyFailed': (422, 'verify_failed'),
            'EditError': (400, 'edit_error'), 'LayoutChanged': (409, 'layout_changed'), 'TooBig': (507, 'too_big'), 'OutputUnreadable': (422, 'output_unreadable'), 'BadDest': (400, 'bad_dest'), 'CloudPlaceholder': (409, 'cloud_placeholder'), 'UnsupportedVersion': (415, 'unsupported_version'), 'DiskError': (507, 'disk_error')}.get(n, (500, 'error'))


def result_json(r):
    return {'ok': True, 'dest': r.dest, 'size': r.size, 'sha256': r.sha256[:12], 'backup': r.backup, 'version': r.version,
            'elapsed': round(r.elapsed, 3), 'verify': r.report}


def _stage(ss, mid, text):
    import time
    p = ss.progress.setdefault(mid, {'t0': time.time()}); p['stage'] = text; p['t'] = time.time()


def _pending(ss, mid, d, new_bytes, manifest):
    """bytes + manifest of the recorded edits replayed on the loaded bytes (explicit new_bytes win)"""
    if new_bytes is not None: return new_bytes, manifest or {}
    from .edit import apply_full, Edits
    e = ss.edits(mid); ops = list(e.ops); ss.applied[mid] = len(ops)
    nb, deleted = apply_full(d.buf, ops); m = Edits(); m.ops = ops
    return nb, m.manifest(deleted)


def _cloud_gate(*paths):
    from . import plat
    for f in paths:
        if f and plat.fsio.is_cloud_placeholder(f):
            raise CloudPlaceholder('the file is an online-only cloud placeholder (OneDrive/Dropbox) that is not downloaded yet; make it available offline first, then retry (nothing written): ' + f)


def save_as(ss, mid, src, dest, overwrite=False, new_bytes=None, manifest=None):
    """SAVE AS: never touches the source. new_bytes defaults to the loaded bytes (identity save)."""
    _cloud_gate(src, dest); ss.progress.pop(mid, None); _stage(ss, mid, 'applying edits'); d = ss.doc(mid, src); d.adapter.report = lambda t: _stage(ss, mid, t)
    new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest); _stage(ss, mid, 'verifying and writing')
    r = result_json(_guard(_import().save_as, d, new_bytes, dest, manifest, overwrite=overwrite))
    lc = layout_changes(d.buf, new_bytes) if new_bytes is not d.buf else []
    if lc is None: r['warnings'] = ['the page-layout check could not run: this output is NOT confirmed to keep the layout of the source']
    elif lc: r['warnings'] = ['page layout of %s changed (%s -> %s, %+d bytes): this layout is NOT confirmed to open in Revit; verify the copy in Revit before relying on it' % (k, la, lb, dz) for k, la, lb, dz in lc]
    return r


def save_overwrite(ss, mid, src, force=False, new_bytes=None, manifest=None):
    """SAVE! : overwrite the source (needs allow_overwrite + open gate; Conflict if the file changed since load unless force)"""
    _cloud_gate(src); ss.progress.pop(mid, None); _stage(ss, mid, 'applying edits'); d = ss.doc(mid, src); d.adapter.report = lambda t: _stage(ss, mid, t)
    new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest); _stage(ss, mid, 'verifying and writing')
    lc = layout_changes(d.buf, new_bytes) if new_bytes is not d.buf else []
    if lc is None and os.environ.get('RVTBALLET_ALLOW_LAYOUT_CHANGE') != '1': raise LayoutChanged('overwrite refused: the page-layout check could not run, so the output is not known to keep the source layout. Use SAVE AS (override: RVTBALLET_ALLOW_LAYOUT_CHANGE=1).')
    if lc and os.environ.get('RVTBALLET_ALLOW_LAYOUT_CHANGE') != '1':
        raise LayoutChanged('overwrite refused: the page layout of %s would change (%s -> %s, %+d bytes) and this is not confirmed to open in Revit. Use SAVE AS and check the copy (override: RVTBALLET_ALLOW_LAYOUT_CHANGE=1).' % (lc[0][0], lc[0][1], lc[0][2], lc[0][3]))
    r = result_json(_guard(_import().save, d, new_bytes, manifest, force=force))
    del ss.edits(mid).ops[:ss.applied.pop(mid, 0)]          # only the ops that were applied are in the file now
    return r


def backups(src):
    sg = _import()
    import time
    return [{'n': i, 'name': n, 'path': p, 'size': sz, 'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(p).st_mtime))}
            for i, (n, p, sz) in enumerate(sg.list_backups(src))]


def restore_backup(ss, mid, src, n=0):
    """put backup n (0 = newest) back over the source (savegate backs the current file up first); the doc is re-opened so the fingerprint matches"""
    sg = _import(); ss.close(mid); ss.edits(mid).ops.clear()      # pending edits were recorded against the old content
    used = sg.restore(src, n)
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


def add_edit(ss, mid, src, op):
    """record an edit after a trial replay on the loaded bytes (so an op the writer cannot apply is refused now, not at save time)"""
    from .edit import apply_full, validate_op
    d = ss.doc(mid, src); e = ss.edits(mid); op = validate_op(op); _, deleted = apply_full(d.buf, e.ops + [op])
    e.ops.append(op)
    return {'ok': True, 'n': len(e.ops), 'ops': e.ops, 'manifest': e.manifest(deleted)}


class BadDest(Exception): pass


def check_dest(dest, src):
    """SAVE AS destination sanity, before anything is read or verified. Raises BadDest."""
    if not isinstance(dest, str) or not dest.strip(): raise BadDest('destination path required')
    if '\0' in dest or len(dest) > 4096: raise BadDest('destination path is invalid (NUL or too long)')
    if not os.path.isabs(dest): raise BadDest('destination must be an absolute path')
    if os.path.basename(dest) in ('', '.', '..') or dest.endswith(('/', os.sep)): raise BadDest('destination must name a file')
    d = os.path.dirname(dest)
    if not os.path.isdir(d): raise BadDest('destination folder does not exist: %s' % d)
    if os.path.lexists(dest) and not os.path.isfile(dest) and not os.path.islink(dest): raise BadDest('destination exists and is not a regular file')
    same = os.path.normcase(os.path.realpath(dest)) == os.path.normcase(os.path.realpath(src))
    try: same = same or (os.path.exists(dest) and os.path.samefile(dest, src))      # case-insensitive filesystems, hard links
    except OSError: pass
    if same: raise BadDest('destination is the source file (use SAVE to overwrite)')
    return dest


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
