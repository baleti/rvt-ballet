"""Stress: 20 cycles of SAVE! (alternating move +1 / -1 of one element) with a restore of the previous state every 4th cycle. After every step the file must equal the expected bytes (hash), no temp files may remain, and at least one backup must exist at the end (retention of the first backup is not asserted; 20 were kept)."""
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
f = _T + '/w.rte'; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); sign = 1.0; hist = [h0]
for i in range(1, 21):
    d = ss.doc('m', f)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': sign})])
    save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(f) == hashlib.sha256(nb).hexdigest(), 'cycle %d: file != saved bytes' % i
    hist.append(sha(f)); sign = -sign
    if i % 4 == 0:
        save.restore_backup(ss, 'm', f, 0); hist.append(sha(f)); assert sha(f) == hist[-3], 'cycle %d: restore did not return the previous state' % i
    left = [x for x in os.listdir(_T) if x.endswith('.tmp') or '.tmp' in x]; assert not left, left
bl = save.backups(f); assert len(bl) > 0, bl
print('save cycles OK', len(hist), 'states, backups kept', len(bl))
