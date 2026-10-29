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

class SaveSessions:
    """one savegate Doc per model id, opened lazily from the source .rvt (fingerprint taken at first use = load time)"""
    def __init__(self, cfg=None):
        self.docs = {}; self.ed = {}; self._cfg = cfg
    @property
    def cfg(self):
        """Config(allow_overwrite from env RVTBALLET_ALLOW_OVERWRITE=1; the oracle gate stays on)"""
        if self._cfg is not None: return self._cfg
        sg = _import()
        return sg.Config(allow_overwrite=os.environ.get('RVTBALLET_ALLOW_OVERWRITE') == '1') if sg else None
    @property
    def available(self): return _import() is not None
    def doc(self, mid, src):
        sg = _import()
        if sg is None: raise RuntimeError('savegate is not installed')
        d = self.docs.get(mid)
        if d is None or d.path != os.path.abspath(src):
            from savegate.adapters import RvtAdapter
            from savegate import rvt_elements
            d = sg.open_doc(src, RvtAdapter(elements_fn=rvt_elements.elements), cfg=self.cfg)      # element-level verify
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


def error_status(exc):
    """savegate exception -> (http status, machine code)"""
    n = type(exc).__name__
    return {'Conflict': (409, 'conflict'), 'GateClosed': (409, 'gate_closed'), 'OverwriteDisabled': (409, 'overwrite_disabled'),
            'Exists': (409, 'exists'), 'Locked': (423, 'locked'), 'VerifyFailed': (422, 'verify_failed'),
            'EditError': (400, 'edit_error'), 'UnsupportedVersion': (415, 'unsupported_version'), 'DiskError': (507, 'disk_error')}.get(n, (500, 'error'))


def result_json(r):
    return {'ok': True, 'dest': r.dest, 'size': r.size, 'sha256': r.sha256[:12], 'backup': r.backup, 'version': r.version,
            'elapsed': round(r.elapsed, 3), 'verify': r.report}


def _pending(ss, mid, d, new_bytes, manifest):
    """bytes + manifest of the recorded edits replayed on the loaded bytes (explicit new_bytes win)"""
    if new_bytes is not None: return new_bytes, manifest or {}
    from .edit import apply
    e = ss.edits(mid)
    return apply(d.buf, e.ops), e.manifest()


def save_as(ss, mid, src, dest, overwrite=False, new_bytes=None, manifest=None):
    """SAVE AS: never touches the source. new_bytes defaults to the loaded bytes (identity save)."""
    d = ss.doc(mid, src); new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest)
    return result_json(_import().save_as(d, new_bytes, dest, manifest, overwrite=overwrite))


def save_overwrite(ss, mid, src, force=False, new_bytes=None, manifest=None):
    """SAVE! : overwrite the source (needs allow_overwrite + open gate; Conflict if the file changed since load unless force)"""
    d = ss.doc(mid, src); new_bytes, manifest = _pending(ss, mid, d, new_bytes, manifest)
    r = result_json(_import().save(d, new_bytes, manifest, force=force))
    ss.edits(mid).ops.clear()                      # the edits are in the file now
    return r


def backups(src):
    sg = _import()
    import time
    return [{'n': i, 'name': n, 'path': p, 'size': sz, 'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(p).st_mtime))}
            for i, (n, p, sz) in enumerate(sg.list_backups(src))]


def restore_backup(ss, mid, src, n=0):
    """put backup n (0 = newest) back over the source (savegate backs the current file up first); the doc is re-opened so the fingerprint matches"""
    sg = _import(); ss.close(mid)
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
    from .edit import apply, validate_op
    d = ss.doc(mid, src); e = ss.edits(mid); op = validate_op(op); apply(d.buf, e.ops + [op])
    e.ops.append(op)
    return {'ok': True, 'n': len(e.ops), 'ops': e.ops, 'manifest': e.manifest()}
