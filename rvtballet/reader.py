"""Thin adapter over the pure-Python .rvt reader in ~/rvt-research (read-only dependency, never edited here).
Everything the viewer needs from the reader goes through this module, so reader changes only touch one place.
Override the reader location with RVT_READER_DIR."""
import os, sys, pickle, hashlib, time
from . import plat

READER_DIR = os.environ.get('RVT_READER_DIR') or plat.paths.reader_dir(os.path.dirname(os.path.abspath(__file__))) or os.path.expanduser('~/rvt-research')
CACHE_DIR = os.environ.get('RVT_BALLET_CACHE', plat.dirs.cache_dir('rvt-ballet'))

def _import():
    if READER_DIR not in sys.path: sys.path.insert(0, READER_DIR)
    os.environ['RVT_GEOM'] = '1'
    import rvt_entities, rvt_params, rvt_scan
    return rvt_entities, rvt_params, rvt_scan

def reader_stamp():
    """changes whenever any reader module / table / GEOMETRY_API.md changes (cache key: a reader upgrade invalidates converted models)"""
    import glob
    h = hashlib.md5()
    files = sorted(glob.glob(os.path.join(READER_DIR, 'rvt*.py')) + glob.glob(os.path.join(READER_DIR, 'ifcguid.py')) + glob.glob(os.path.join(READER_DIR, 'map3_train.json')) + glob.glob(os.path.join(READER_DIR, 'GEOMETRY_API.md')))
    for f in files:
        try: st = os.stat(f); h.update(('%s:%d:%d' % (os.path.basename(f), int(st.st_mtime), st.st_size)).encode())
        except OSError: pass
    return h.hexdigest()[:8]

def viewer_stamp():
    """hash of this project's converter sources (geometry code change also invalidates caches)"""
    import glob
    h = hashlib.md5(); d = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(glob.glob(os.path.join(d, '*.py'))):
        if os.path.basename(f) in ('server.py', 'cli.py'): continue
        h.update(open(f, 'rb').read())
    return h.hexdigest()[:8]

def load(path, log=print):
    """-> dict: recs {(id, class): record}, eh {id: header fields}, params {id: {class, params}}, W, classes [names], idsize"""
    E, P, S = _import()
    t = time.time()
    import threading
    stop = threading.Event()
    def beat():
        log('decoding %s (first open of a file runs the pure-Python reader: seconds for small files, minutes for big ones; later opens are instant) ...' % os.path.basename(path))
        while not stop.wait(15): log('  ... still decoding, %ds elapsed (%.0f MB file)' % (time.time() - t, os.path.getsize(path) / 1e6))
    threading.Thread(target=beat, daemon=True).start()
    try:
        import rvt_xcache
        x = rvt_xcache.get_x(path)                 # reader's own shared extraction cache (also used by rvt_params)
    except ImportError:
        x = E.extract(path, want_all=True)
    try: par = P.params(path)
    except Exception as ex:                        # reader bug on odd files (NEEDS-FROM-READER item 29, corpus-031): open without parameters rather than not at all
        log('WARNING: parameter extraction failed (%r): opening without element parameters' % ex); par = {}
    stop.set()
    names = x['sch'].c if 'sch' in x else S.load(path)[1]
    log('reader: %d records, %d headers, %d param sets in %.1fs' % (len(x['recs']), len(x['eh']), len(par), time.time() - t))
    return {'recs': x['recs'], 'eh': x['eh'], 'W': x['W'], 'params': par,
            'classes': [c['name'] for c in names], 'tagbase': 12}

def cached_load(path, log=print):
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader_stamp())).encode()).hexdigest()
    fn = os.path.join(CACHE_DIR, 'raw-' + key + '.pkl')
    _import()
    if os.path.exists(fn):
        t = time.time()
        try: d = pickle.load(open(fn, 'rb')); log('raw cache hit (%.1fs)' % (time.time() - t)); return d
        except Exception as ex:                                  # truncated by a killed run: drop it and decode again
            log('raw cache unreadable (%r): rebuilding' % ex); os.remove(fn)
    d = load(path, log)
    pickle.dump(d, open(fn + '.%d.tmp' % os.getpid(), 'wb'), protocol=pickle.HIGHEST_PROTOCOL); os.replace(fn + '.%d.tmp' % os.getpid(), fn)       # atomic: a killed run never leaves a half-written cache
    return d

def category_names():
    import json
    return json.load(open(os.path.join(os.path.dirname(__file__), 'data', 'category_names.json')))

def document_info(path):
    """parse() output: levels/grids/rooms/views/sheets/phases summary (one more extract pass; cached by caller)"""
    E, P, S = _import()
    return E.parse(path)
