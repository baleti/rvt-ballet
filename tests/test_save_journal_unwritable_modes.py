"""c1x-rvtsave 214: SAVEGATE_JOURNAL unwritable (read-only dir, or a regular file in its place): in-place save must either succeed with source consistent or refuse BEFORE touching the source; never a half state. Synthetic 2024 .rte."""
import os, sys, tempfile, shutil, hashlib, stat
T = tempfile.mkdtemp()
os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/src/savegate'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
if os.geteuid() == 0: print('skip: root ignores modes'); sys.exit(0)
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
for kind in ('readonly_dir', 'file_in_place'):
    j = T + '/j_' + kind
    if kind == 'readonly_dir': os.makedirs(j); os.chmod(j, 0o500)
    else: open(j, 'w').write('not a dir')
    os.environ['SAVEGATE_JOURNAL'] = j
    d = tempfile.mkdtemp(dir=T); src = d + '/m.rvt'; shutil.copy(S, src); h0 = sha(src)
    try:
        ss = save.SaveSessions(__import__('savegate').Config(allow_overwrite=True, require_gate=False)); dd = ss.doc('m', src)
        nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
        save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']})
        res = 'saved'; assert sha(src) == hashlib.sha256(nb).hexdigest(), 'saved but not the edited bytes'
    except Exception as e:
        res = 'refused: %s %s' % (type(e).__name__, str(e)[:60]); assert sha(src) == h0, 'refused but source changed'
    left = [f for f in os.listdir(d) if f != 'm.rvt']
    print(kind, res, '| leftovers', left)
    assert not [f for f in left if f.endswith('.sgtmp')], 'temp left'
    os.chmod(j, 0o700) if os.path.isdir(j) else None
print('OK')
