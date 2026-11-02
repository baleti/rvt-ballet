"""inject_eio_save_rvt.py FILE.rvt|.rte OPJSON : raise OSError(EIO) ONCE at each fsync/replace/rename/unlink/link call of an in-place save_overwrite (exception injection, the sibling of kill_every_call_rvt.py SIGKILL). Per call: refused with the original byte-identical, or saved with an ok-validating file AND a hash-equal backup present. PERSIST=1: every call from k on fails (persistent EIO). Prints per-call lines + a summary."""
import os, sys, json, shutil, tempfile, hashlib, glob
T = tempfile.mkdtemp()
open(T+'/c.json','w').write('{"allow_overwrite": true}'); open(T+'/g.json','w').write('{"rvt": {"*": "open"}}')
os.environ.update(SAVEGATE_JOURNAL=T+'/j', SAVEGATE_CACHE=T+'/c', DWG_BALLET_CONFIG=T+'/c.json', SAVEGATE_GATE=T+'/g.json', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_LAYOUT_CHANGE='1')
sys.path[:0] = [os.path.expanduser('~/src/rvt-viewer'), os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research')]
from rvtballet import save
src = sys.argv[1]; sha = lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest(); h0 = sha(src)
op = json.loads(sys.argv[2]); calls = ('fsync','replace','rename','unlink','link')
names = []
def attempt(fail):
    d = tempfile.mkdtemp(dir=T); p = d+'/a.rvt'; shutil.copy(src, p)
    ss = save.SaveSessions(); ss.doc('m', p); save.add_edit(ss, 'm', p, dict(op)); n = [0]; orig = {c: getattr(os, c) for c in calls}
    def wrap(c):
        def g(*a, **k):
            n[0] += 1
            if fail and (n[0] >= fail if os.environ.get('PERSIST') else n[0] == fail): names.append(c); raise OSError(5, 'injected EIO at call %d (%s)' % (fail, c))
            return orig[c](*a, **k)
        return g
    for c in calls: setattr(os, c, wrap(c))
    try: save.save_overwrite(ss, 'm', p); res = 'saved'
    except BaseException as e: res = 'raised ' + type(e).__name__
    finally:
        for c in calls: setattr(os, c, orig[c])
    stray = [x for x in glob.glob(d+'/*')+glob.glob(d+'/.*') if os.path.basename(x) != 'a.rvt' and os.path.isfile(x) and not os.path.basename(x).startswith('.savegate')]
    ok = ''
    bks = [x for pat in (d+'/.savegate/*', T+'/c/*/*') for x in glob.glob(pat) if os.path.isfile(x) and not x.endswith('.part')]
    hb = any(sha(x) == h0 for x in bks)
    if res == 'saved':
        from savegate.adapters import RvtAdapter
        ok = str(RvtAdapter().validate(open(p,'rb').read()))[:20]
    return res + ' ' + ok + (' BACKUP=' + str(hb) if res == 'saved' else ''), sha(p) == h0, n[0], stray
r0 = attempt(0); total = r0[2]; print('warm', r0, flush=True); out = {}
for k in range(1, total+1):
    res, same, _, stray = attempt(k); print(k, names[-1:], res, 'orig' if same else 'CHANGED', stray, flush=True)
    key = (res, 'orig' if same else 'changed', bool(stray)); out[key] = out.get(key, 0) + 1
print(out)
