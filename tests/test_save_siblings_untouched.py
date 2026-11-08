"""c1x-rvtsave 230: in-place save next to Revit-style sibling files (x.0001.rte backup, x_backup/ folder with a Revit journal-like file, x.rte.lock, unrelated x2.rte): every sibling byte-identical and mtime unchanged after the save; only the source changes (plus the savegate backup folder). Synthetic 2024 .rte."""
import os, sys, tempfile, shutil, hashlib, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(); D = T + '/proj'; os.makedirs(D + '/x_backup')
json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE=T + '/s', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_ALLOW_LAYOUT_CHANGE='1', SAVEGATE_GATE=T + '/gate.json')
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = D + '/x.rte'; shutil.copy(S, p)
sib = [D + '/x.0001.rte', D + '/x2.rte', D + '/x.rte.lock', D + '/x_backup/Journal.0001.txt']
shutil.copy(S, sib[0]); shutil.copy(S, sib[1]); open(sib[2], 'w').write('locked by someone'); open(sib[3], 'w').write('journal')
before = {s: (sha(s), os.stat(s).st_mtime_ns) for s in sib}; h0 = sha(p)
ss = save.SaveSessions(); dd = ss.doc('m', p)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(p) != h0
for s in sib: assert (sha(s), os.stat(s).st_mtime_ns) == before[s], ('sibling changed', os.path.basename(s))
extra = sorted(set(os.listdir(D)) - {'x.rte', 'x.0001.rte', 'x2.rte', 'x.rte.lock', 'x_backup'}); print('new entries next to the source:', extra)
shutil.rmtree(T, ignore_errors=True); print('OK')
