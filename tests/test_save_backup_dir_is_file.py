"""The .savegate backup location is a regular FILE (or a dangling symlink): in-place SAVE! must refuse and leave the model byte-identical, no temp left."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); M = tempfile.mkdtemp(dir=T)
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
for kind in ('file', 'dangling'):
    p = M + '/m_%s.rte' % kind; shutil.copy(S, p); h0 = sha(p); bd = M + '/.savegate'
    if os.path.lexists(bd): os.remove(bd)
    if kind == 'file': open(bd, 'w').write('not a dir')
    else: os.symlink(T + '/nowhere/x', bd)
    ss = save.SaveSessions(); d = ss.doc('m' + kind, p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    try: save.save_overwrite(ss, 'm' + kind, p, new_bytes=nb, manifest={'modified': ['el:301595']}); saved = True
    except Exception as e: saved = False; err = str(e)[:100]
    if saved:
        bl = save.backups(p); print(kind, 'saved; backups:', [(b['path'], sha(b['path']) == h0) for b in bl], 'bd is dir:', os.path.isdir(bd)); assert bl and sha(bl[0]['path']) == h0, 'saved WITHOUT a valid backup of the original'
    else: assert sha(p) == h0, 'refused but model changed'; print(kind, 'refused cleanly:', err)
    left = [f for f in os.listdir(M) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
shutil.rmtree(T); print('ok')
