"""Pending-edit store is replayed only against the exact bytes it was recorded for: other sha, missing sha, truncated json, wrong types, a store of another file with the same name: none returns ops; a mismatching store is kept."""
import os, sys, json, tempfile, shutil
T = tempfile.mkdtemp(); os.environ['RVTBALLET_EDITSTORE'] = T + '/store'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import editstore as es
try:
    os.makedirs(T + '/a'); os.makedirs(T + '/b')
    a = T + '/a/m.rvt'; b = T + '/b/m.rvt'; open(a, 'w').write('x'); open(b, 'w').write('x')
    ops = [{'op': 'move', 'eid': 1, 'dx': 1.0}]
    es.sync(a, ops, 'S1')
    assert es.load(a, 'S1') == (ops, None)
    o, why = es.load(a, 'S2'); assert o == [] and 'changed' in why
    assert os.path.exists(es._file(a)), 'mismatching store must be kept'
    assert es.load(a, 'S1')[0] == ops, 'kept store still usable by the right file'
    assert es.load(b, 'S1') == ([], None), 'same name in another dir is another store'
    p = es._file(a); good = open(p).read()
    for bad in (good[:len(good) // 2], '', '[]', 'null', json.dumps({'sha256': 'S1', 'ops': 'x'}), json.dumps({'ops': ops}), json.dumps({'sha256': 'S1', 'ops': {'a': 1}})):
        open(p, 'w').write(bad); o, why = es.load(a, 'S1'); assert o == [] and why, (bad[:30], o, why)
    es.sync(a, [], 'S1'); assert es.load(a, 'S1') == ([], None)
    print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
