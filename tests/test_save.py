"""rvtballet.save: import-optional, fingerprint at open, doc cached per model id."""
import os, sys, tempfile, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save

def main():
    ss = save.SaveSessions()
    assert ss.info('x', None) == {'available': ss.available, 'open': False}
    assert ss.info('x', '/nonexistent.rvt')['open'] is False
    if not ss.available:
        print('savegate missing: only degrade path tested'); return
    d = tempfile.mkdtemp(); p = os.path.join(d, 'a.rvt'); open(p, 'wb').write(b'not a revit file')
    r = ss.info('x', p); assert r['open'] is False and ('unknown' in r['error'].lower() or 'unsupported' in r['error'].lower()), r
    print('save adapter OK')
main()
