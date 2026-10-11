"""Thin adapter over the pure-Python .rvt reader in ~/rvt-research (read-only dependency, never edited here).
Everything the viewer needs from the reader goes through this module, so reader changes only touch one place.
Override the reader location with RVT_READER_DIR."""
import os, sys, pickle, hashlib, time

READER_DIR = os.environ.get('RVT_READER_DIR', os.path.expanduser('~/rvt-research'))
CACHE_DIR = os.environ.get('RVT_VIEWER_CACHE', os.path.expanduser('~/.cache/rvt-viewer'))

def _import():
    if READER_DIR not in sys.path: sys.path.insert(0, READER_DIR)
    os.environ['RVT_GEOM'] = '1'
    import rvt_entities, rvt_params, rvt_scan
    return rvt_entities, rvt_params, rvt_scan

def reader_stamp():
    """changes whenever the reader's decoder/param code changes (cache key)"""
    h = hashlib.md5()
    for f in ('rvt_decode.py', 'rvt_entities.py', 'rvt_params.py', 'rvt_geom.py', 'rvt_map2.py', 'map3_train.json'):
        try: h.update(str(int(os.path.getmtime(os.path.join(READER_DIR, f)))).encode())
        except OSError: pass
    return h.hexdigest()[:8]

def load(path, log=print):
    """-> dict: recs {(id, class): record}, eh {id: header fields}, params {id: {class, params}}, W, classes [names], idsize"""
    E, P, S = _import()
    t = time.time()
    orig = E.extract; memo = {}
    def shared(p, *a, **k):
        key = (p, tuple(a), tuple(sorted(k.items())))
        if key not in memo: memo[key] = orig(p, *a, **k)
        return memo[key]
    E.extract = shared; P.E.extract = shared
    try:
        par = P.params(path)
    finally:
        E.extract = orig; P.E.extract = orig
    x = next(iter(memo.values()))
    log('reader: %d records, %d headers, %d param sets in %.1fs' % (len(x['recs']), len(x['eh']), len(par), time.time() - t))
    return {'recs': x['recs'], 'eh': x['eh'], 'W': x['W'], 'params': par,
            'classes': [c['name'] for c in x['sch'].c], 'tagbase': 12}

def cached_load(path, log=print):
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader_stamp())).encode()).hexdigest()
    fn = os.path.join(CACHE_DIR, 'raw-' + key + '.pkl')
    _import()
    if os.path.exists(fn):
        t = time.time(); d = pickle.load(open(fn, 'rb')); log('raw cache hit (%.1fs)' % (time.time() - t)); return d
    d = load(path, log)
    pickle.dump(d, open(fn, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
    return d

def category_names():
    import json
    return json.load(open(os.path.join(os.path.dirname(__file__), 'data', 'category_names.json')))

def document_info(path):
    """parse() output: levels/grids/rooms/views/sheets/phases summary (one more extract pass; cached by caller)"""
    E, P, S = _import()
    return E.parse(path)
