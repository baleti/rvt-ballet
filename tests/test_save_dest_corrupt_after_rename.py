"""The destination is corrupted between the atomic rename and the gate's final sha check (simulated via the atomic hook: bit flip / truncation after 'after_replace'): the save must raise (never report success), and the gate must restore the original bytes in place (hook fires once, so the restore itself is clean). Skips when the scene is unavailable."""
import os, sys, tempfile, shutil, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
T = tempfile.mkdtemp()
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg
from savegate import atomic
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(mode):
    d = tempfile.mkdtemp(dir=T); src = d + '/src.rvt'; shutil.copy(RTE, src); h0 = sha(src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False, backup_dir=d + '/bk') if 'backup_dir' in sg.Config.__dataclass_fields__ else sg.Config(allow_overwrite=True, require_gate=False, verify=False))
    dd = ss.doc('m', src)
    nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    fired = []
    def hook(step):
        if step != 'after_replace' or fired: return
        fired.append(1)
        b = bytearray(open(src, 'rb').read())
        if mode == 'flip': b[len(b) // 2] ^= 0xFF
        else: b = b[:len(b) - 4096]
        open(src, 'wb').write(bytes(b))
    atomic._hook = hook
    try:
        try: save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); return mode, 'UNEXPECTED OK (corrupt dest accepted)', False
        except Exception as e: err = type(e).__name__
    finally: atomic._hook = None
    same = sha(src) == h0
    bk = [os.path.join(r, f) for r, _, fs in os.walk(T) for f in fs if sha(os.path.join(r, f)) == h0 and os.path.join(r, f) != src]
    return mode, err + ' orig_in_place=%s backup_copy=%s' % (same, bool(bk)), same or bool(bk)
bad = 0
for m in ('flip', 'trunc'):
    r = run(m); print(*r); bad += not r[2]
shutil.rmtree(T, ignore_errors=True)
assert not bad, 'unrecoverable'; print('OK')
