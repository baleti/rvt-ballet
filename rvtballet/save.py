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
        self.docs = {}; self.cfg = cfg
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
