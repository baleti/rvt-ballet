"""An OSError (disk full, file too large) while save_overwrite checks group/design-option membership is reported as disk_error (507), not as a group/option refusal; file untouched."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); return
    src = _T + '/s.rvt'; shutil.copy(RTE, src); h = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
    ss.edits('m').ops.append({'op': 'set_string', 'eid': 24, 'value': 'x', 'match': ''})
    def boom(*a, **k): raise OSError(28, 'No space left on device')
    old = save.membership; save.membership = boom
    try:
        try: save.save_overwrite(ss, 'm', src); raise SystemExit('FAIL: no error')
        except save.DiskError as e: assert 'disk error' in str(e)
    finally: save.membership = old
    assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h
    print('membership oserror OK')
main()
