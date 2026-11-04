"""(many ops in one save) 30 elements of the 2024 cols2 scene moved by different amounts in ONE in-place SAVE!: accepted with file == edited bytes, or refused with the original intact. Keeps the output in KEEP_OUT if set."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ss = save.SaveSessions()
p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p); d = ss.doc('m', p)
E = [301553,301554,301555,301556,301557,301558,301559,301560,301561,301562,301563,301564,301565,301581,301583,301584,301585,301586,301592,301593,301594,301595,301596,301597,301598,301599,301600,301601,301602,301603]
d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': e, 'dx': 0.5 + i * 0.25, 'dy': -0.1 * i}) for i, e in enumerate(E)])
try:
    save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % e for e in E]})
    assert sha(p) == hashlib.sha256(nb).hexdigest(); print('ACCEPTED 30 moves, file == edited bytes')
    if os.environ.get('KEEP_OUT'): shutil.copy(p, os.environ['KEEP_OUT'])
except Exception as e:
    assert sha(p) == h0, 'refused but file changed'; print('REFUSED', type(e).__name__, str(e)[:200], '- original intact')
