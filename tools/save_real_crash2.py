"""SIGKILL at every savegate step with a REAL EDIT on a COPY of a real project (temp gate, in-process child): SAVE AS and overwrite, REPS kills per (mode, step). Invariants: after the kill the source is exactly the OLD or exactly the NEW
bytes (never a mix), a SAVE AS target is absent or exactly the NEW bytes, no *.sgtmp / .part leftovers except the journal-listed recoverable one, save.recoverable lists the killed session, and a later normal overwrite
of the same copy still works (no stale lock). Aggregate output only. usage: tools/save_real_crash2.py FILE [REPS]"""
import os, sys, tempfile, hashlib, shutil, subprocess, signal, json
_T = tempfile.mkdtemp(); J = _T + '/j'; C = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import os, sys, signal, json
sys.path.insert(0, %(here)r)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg, savegate.atomic as A
step, mode, src, dest, newf = sys.argv[1:6]
new = open(newf, 'rb').read()
def hook(s):
    if s == step: os.kill(os.getpid(), signal.SIGKILL)
A._hook = hook
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
man = {'modified': json.load(open(newf + '.man'))}
if mode == 'saveas': save.save_as(ss, 'm', src, dest, new_bytes=new, manifest=man)
else: save.save_overwrite(ss, 'm', src, new_bytes=new, manifest=man)
'''
def main(src0, reps):
    sys.path.insert(0, HERE); os.environ['SAVEGATE_JOURNAL'] = J; os.environ['SAVEGATE_CACHE'] = C; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
    for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
    from rvtballet import save, edit
    import rvt_params
    save._import(); old = open(src0, 'rb').read(); h_old = hashlib.sha256(old).hexdigest()
    pr = rvt_params.params(src0); eid = next(e for e, d in pr.items() if (d.get('params', d) if isinstance(d, dict) else {}).get('Comments') == '')
    op = edit.validate_op({'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'crash test edit'}); new, _ = edit.apply_full(old, [op]); h_new = hashlib.sha256(new).hexdigest(); assert h_new != h_old
    newf = os.path.join(_T, 'new.rvt'); open(newf, 'wb').write(new); json.dump(['el:%d' % eid], open(newf + '.man', 'w'))
    res = {'kills': 0, 'old': 0, 'new': 0, 'mixed': 0, 'saveas_target_partial': 0, 'not_listed': 0, 'later_save_fail': 0}
    for mode in ('saveas', 'overwrite'):
        for step in ('tmp_written', 'before_replace', 'after_replace'):
            for rep in range(reps):
                d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'src.rvt'); shutil.copy(src0, src); dest = os.path.join(d, 'out.rvt')
                env = dict(os.environ, SAVEGATE_JOURNAL=J, SAVEGATE_CACHE=C)
                r = subprocess.run([sys.executable, '-c', CHILD % {'here': HERE}, step, mode, src, dest, newf], env=env, capture_output=True, text=True, timeout=900)
                assert r.returncode == -signal.SIGKILL, (mode, step, r.returncode, r.stderr[-300:]); res['kills'] += 1
                h = sha(src); res['old' if h == h_old else 'new' if h == h_new else 'mixed'] += 1
                if mode == 'saveas' and os.path.exists(dest) and sha(dest) != h_new: res['saveas_target_partial'] += 1
                if mode == 'saveas': assert h == h_old
                if not [x for x in save.recoverable(save.SaveSessions()) if x['source'] == src]: res['not_listed'] += 1
                try:
                    import savegate as sg
                    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m2', src); save.save_overwrite(ss, 'm2', src, new_bytes=new, manifest={'modified': json.load(open(newf + '.man'))}); assert sha(src) == h_new
                except Exception as e: res['later_save_fail'] += 1; print('later save failed:', type(e).__name__, str(e)[:100])
                shutil.rmtree(d, ignore_errors=True)
    print('REAL-CRASH', res, 'OK' if res['mixed'] == res['saveas_target_partial'] == res['not_listed'] == res['later_save_fail'] == 0 else 'PROBLEM')
main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
