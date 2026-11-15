"""In-place save through a symlinked DIRECTORY that is re-pointed to another directory between the temp write and the rename (hook 'before_replace'): the save must not report success with the wrong file replaced; neither directory's .rvt may end up damaged or replaced by an unverified file. Reports what happened to temp litter."""
import os, sys, tempfile, shutil, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
T = tempfile.mkdtemp()
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import(); import savegate as sg
from savegate import atomic
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    A = T + '/A'; B = T + '/B'; os.makedirs(A); os.makedirs(B); L = T + '/L'; os.symlink(A, L)
    shutil.copy(RTE, A + '/x.rvt'); shutil.copy(RTE, B + '/x.rvt'); hA = sha(A + '/x.rvt')
    # B holds a DIFFERENT valid file so a wrong replace is detectable
    b = bytearray(open(B + '/x.rvt', 'rb').read()); open(B + '/x.rvt', 'wb').write(bytes(b)); hB = sha(B + '/x.rvt')
    src = L + '/x.rvt'
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
    nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    def hook(step):
        if step == 'before_replace' and os.path.islink(L): os.remove(L); os.symlink(B, L)
    atomic._hook = hook
    try: save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'saved'
    except Exception as e: res = 'refused ' + type(e).__name__ + ': ' + str(e)[:80]
    finally: atomic._hook = None
    nbh = hashlib.sha256(nb).hexdigest()
    a_state = 'orig' if sha(A + '/x.rvt') == hA else ('NEW' if sha(A + '/x.rvt') == nbh else 'OTHER')
    b_state = 'orig' if sha(B + '/x.rvt') == hB else ('NEW' if sha(B + '/x.rvt') == nbh else 'OTHER')
    litter = {d: [f for f in os.listdir(T + '/' + d) if f != 'x.rvt'] for d in 'AB'}
    print(res); print('A', a_state, 'B', b_state, 'litter', litter)
    assert 'OTHER' not in (a_state, b_state), 'a file was damaged'
    if res == 'saved': assert b_state == 'NEW' or a_state == 'NEW', 'success reported but no file got the verified bytes'
    print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
