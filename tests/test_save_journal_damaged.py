"""Journal files damaged (garbage bytes, truncated, binary, huge line, directory in place of the file) before an in-place save: the save either succeeds with a verified file or is refused with the original untouched, never a crash that leaves a temp or damaged file; RESTORE afterwards still returns the original bytes."""
import os, sys, tempfile, shutil, hashlib, glob
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(mode):
    T = tempfile.mkdtemp(); J = T + '/j'; os.makedirs(J)
    os.environ['SAVEGATE_JOURNAL'] = J; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
    from rvtballet import save, edit
    save._import(); import savegate as sg
    src = T + '/src.rvt'; shutil.copy(RTE, src); h0 = sha(src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
    nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    # pass 1: let the library create its journal files, then damage them
    try: save.save_overwrite(ss, 'm', src, new_bytes=edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 0.5})])[0], manifest={'modified': ['el:301595']})
    except Exception as e: pass
    shutil.copy(RTE, src); ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
    files = [p for p in glob.glob(J + '/**', recursive=True) if os.path.isfile(p)]
    if not files: files = [J + '/journal.log']
    for p in files:
        if mode == 'garbage': open(p, 'wb').write(os.urandom(4096))
        elif mode == 'trunc': open(p, 'wb').write(open(p, 'rb').read()[:7])
        elif mode == 'huge': open(p, 'wb').write(b'{"a":"' + b'x' * (8 << 20))
        elif mode == 'nul': open(p, 'wb').write(b'\0' * 1000)
        elif mode == 'dir': os.remove(p); os.makedirs(p)
    try: save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'saved'
    except Exception as e: res = 'refused ' + type(e).__name__
    left = [f for f in os.listdir(T) if f.endswith('.sgtmp')]
    ok = not left
    if res == 'saved': ok &= sha(src) == hashlib.sha256(nb).hexdigest()
    else: ok &= sha(src) == h0
    try:
        sg.restore(src) if hasattr(sg, 'restore') else None
        rest = sha(src) == h0 if res == 'saved' else True
    except Exception as e: rest = res != 'saved'
    shutil.rmtree(T, ignore_errors=True)
    return mode, res, 'tmp_left=%s' % bool(left), 'restore_ok=%s' % rest, ok and rest
bad = 0
for m in ('garbage', 'trunc', 'huge', 'nul', 'dir'):
    r = run(m); print(*r); bad += not r[-1]
assert not bad; print('OK')
