"""c1x-rvtmove item 101: two processes load the SAME original and each does an in-place SAVE! of a DIFFERENT move (cols2 2024 scene, 301595 +1 ft vs +2 ft) released at the same instant.
Invariants: the final file is byte-identical to exactly one of the two verified outputs (never a mix, never the original after a reported success), the loser either reports a refusal
(conflict) or, if it also succeeded, the file is still one complete verified output; no temp leftovers; the original is recoverable from a backup. Offline only, not a VM verdict."""
import os, sys, tempfile, hashlib, shutil, subprocess, json, time
_T = tempfile.mkdtemp(); HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(SRC): print('skip: no scene'); sys.exit(0)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
ENV = dict(os.environ, SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ.update(ENV)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import os, sys, time
sys.path.insert(0, %(here)r)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import save
save._import()
import savegate as sg
src, dx, go = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
save.add_edit(ss, 'm', src, {'op': 'move', 'eid': 301595, 'dx': dx, 'dy': 0.0, 'dz': 0.0})
while time.time() < go: time.sleep(0.005)
try:
    save.save_overwrite(ss, 'm', src); print('SAVED')
except Exception as e: print('REFUSED', type(e).__name__, str(e)[:120])
'''
def expected(dx):
    from rvtballet import save, edit
    save._import(); ss = save.SaveSessions(); d = ss.doc('x%s' % dx, SRC)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': dx, 'dy': 0.0, 'dz': 0.0})]); return hashlib.sha256(nb).hexdigest()
def main():
    from rvtballet import save; save._import()
    h0 = sha(SRC); E = {1.0: expected(1.0), 2.0: expected(2.0)}
    for rnd in range(3):
        d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'src.rvt'); shutil.copy(SRC, src)
        go = time.time() + 40                                    # both children load first (slow), then release together
        ps = [subprocess.Popen([sys.executable, '-c', CHILD % {'here': HERE}, src, str(dx), str(go)], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for dx in (1.0, 2.0)]
        outs = [p.communicate(timeout=900) for p in ps]; res = [o[0].strip().splitlines()[-1] if o[0].strip() else 'ERR ' + o[1][-200:] for o in outs]
        h = sha(src); assert h in E.values(), ('round %d: final file is neither verified output (corrupt mix or original)' % rnd, res, h == h0)
        ok = [r for r in res if r.startswith('SAVED')]; assert ok, ('round %d: nobody reported success but file changed' % rnd, res)
        left = [f for f in os.listdir(d) if 'sgtmp' in f or f.endswith('.part')]; assert not left, ('temp left', left)
        bk = save.backups(src); assert bk and any(sha(b['path']) == h0 for b in bk), ('no backup equal to the original', res)
        print('round', rnd, res, 'final=move+%s' % ('1' if h == E[1.0] else '2'))
    print('race of two in-place move saves OK')
main()
