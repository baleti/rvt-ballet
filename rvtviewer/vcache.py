"""scene cache keys shared by the server (viewctl.py) and the warm job (vscene_worker.py --warm): content based, so a cache warmed on host1 is valid on host3.
key = md5(file name, file size, rvt-sheets code (contents of rvtsheets/*.py), worker code, request)"""
import os, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser('~/.cache/rvt-viewer/vscene')
SHEETS = os.path.expanduser(os.environ.get('RVTSHEETS', '~/src/rvt-sheets'))
_stamp = None


def code_stamp():
    global _stamp
    if _stamp: return _stamp
    h = hashlib.md5()
    for fn in [os.path.join(HERE, 'vscene_worker.py')] + [os.path.join(SHEETS, 'rvtsheets', f) for f in sorted(os.listdir(os.path.join(SHEETS, 'rvtsheets'))) if f.endswith('.py')] if os.path.isdir(os.path.join(SHEETS, 'rvtsheets')) else []:
        try: h.update(open(fn, 'rb').read())
        except OSError: pass
    _stamp = h.hexdigest()[:10]; return _stamp


def cache_fn(src, req):
    h = hashlib.md5(json.dumps([os.path.basename(src), os.stat(src).st_size, req, code_stamp()], sort_keys=True).encode()).hexdigest()[:20]
    return os.path.join(CACHE, h + '.json')
