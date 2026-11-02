import os, sys, json, time, tempfile
_T = tempfile.mkdtemp(); os.environ['RVTBALLET_EDITSTORE'] = _T + '/es'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import editstore as E

def test_sweep(tmp_path):
    os.makedirs(E.DIR, exist_ok=True); live = tmp_path / 'a.rvt'; live.write_bytes(b'x')
    def mk(name, src, age):
        p = os.path.join(E.DIR, name); json.dump({'src': str(src), 'sha256': 'x', 'ops': [{}]}, open(p, 'w')); t = time.time() - age; os.utime(p, (t, t)); return p
    d = 86400
    keep1 = mk('1.json', live, 10 * d)                       # source exists, 10 days: kept
    keep2 = mk('2.json', tmp_path / 'gone.rvt', 2 * d)       # source gone but recent: kept (drive may be unmounted)
    gone1 = mk('3.json', tmp_path / 'gone.rvt', 8 * d)       # source gone, 8 days: swept
    gone2 = mk('4.json', live, 40 * d)                       # 40 days: swept
    tmp = os.path.join(E.DIR, 'x.tmp'); open(tmp, 'w').write('x'); os.utime(tmp, (1, 1))
    assert E.sweep() == 3
    assert os.path.exists(keep1) and os.path.exists(keep2) and not os.path.exists(gone1) and not os.path.exists(gone2) and not os.path.exists(tmp)

def test_sync_roundtrip_and_remove(tmp_path):
    src = tmp_path / 'b.rvt'; src.write_bytes(b'x')
    E.sync(str(src), [{'op': 'move'}], 'abc'); assert E.load(str(src), 'abc') == ([{'op': 'move'}], None)
    assert E.load(str(src), 'zzz')[1]; E.sync(str(src), [], None); assert E.load(str(src), 'abc') == ([], None)
