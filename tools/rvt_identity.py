"""no-edit load + SAVE AS identity: output bytes vs source. usage: tools/rvt_identity.py FILE...  (aggregate: equal bytes?, verify, seconds)"""
import os, sys, tempfile, hashlib, shutil, time, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
ss = save.SaveSessions()
for k, f in enumerate(sys.argv[1:]):
    src = os.path.join(_T, 's%d.rvt' % k); shutil.copy(f, src); d = os.path.join(_T, 'o%d.rvt' % k); t = time.time()
    try:
        save.save_as(ss, 'm%d' % k, src, d); same = open(src, 'rb').read() == open(d, 'rb').read(); r = {'identical': same}
    except Exception as e: r = {'refused': type(e).__name__, 'msg': str(e)[:90]}
    r.update(mb=round(os.path.getsize(src) / 2 ** 20, 1), s=round(time.time() - t, 1)); print(k, json.dumps(r), flush=True); os.path.exists(d) and os.remove(d); os.remove(src)
shutil.rmtree(_T, ignore_errors=True)
