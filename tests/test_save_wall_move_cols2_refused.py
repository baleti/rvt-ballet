"""Synthetic cols2 scene: an in-place move of SWall 301553 is REFUSED (the editor moves the placement origin but not the wall location line, so the wall-line witness and the declared-edit rule fail); the source file is byte-identical afterwards and no temp file is left. Keeps the wall move refused until the editor really moves GLine.m_origin."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
f = _T + '/w.rte'; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
try: nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301553, 'dx': 2.0, 'dy': 0.0})])
except edit.EditError as x:      # the edit layer now refuses wall moves up front (stricter than the gate): source must be untouched
    assert sha(f) == h0; print('wall move cols2 refused at edit time OK:', str(x)[:80]); raise SystemExit(0)
try:
    save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301553']}); raise SystemExit('ACCEPTED a wall move that does not move the location line')
except SystemExit: raise
except Exception as e: print('refused:', type(e).__name__, str(e)[:160])
assert sha(f) == h0, 'refused but the source changed'
assert not [x for x in os.listdir(_T) if '.tmp' in x], 'temp left'
print('wall move cols2 refused OK, source intact')
