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
        self.docs = {}; self._cfg = cfg
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
            d = self.docs[mid] = sg.open_doc(src, cfg=self.cfg)
        return d
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
            'UnsupportedVersion': (415, 'unsupported_version'), 'DiskError': (507, 'disk_error')}.get(n, (500, 'error'))


def result_json(r):
    return {'ok': True, 'dest': r.dest, 'size': r.size, 'sha256': r.sha256[:12], 'backup': r.backup, 'version': r.version,
            'elapsed': round(r.elapsed, 3), 'verify': r.report}


def save_as(ss, mid, src, dest, overwrite=False, new_bytes=None, manifest=None):
    """SAVE AS: never touches the source. new_bytes defaults to the loaded bytes (identity save)."""
    d = ss.doc(mid, src)
    return result_json(_import().save_as(d, d.buf if new_bytes is None else new_bytes, dest, manifest or {}, overwrite=overwrite))


def save_overwrite(ss, mid, src, force=False, new_bytes=None, manifest=None):
    """SAVE! : overwrite the source (needs allow_overwrite + open gate; Conflict if the file changed since load unless force)"""
    d = ss.doc(mid, src)
    return result_json(_import().save(d, d.buf if new_bytes is None else new_bytes, manifest or {}, force=force))
