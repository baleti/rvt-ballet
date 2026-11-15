"""Fresh load, then another program rewrites the file with the SAME size and the SAME mtime (also: mtime rounded to 2 s like FAT): the FIRST in-place save must refuse (content hash), leave that version untouched and write nothing."""
import os, sys, tempfile, shutil, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
T = tempfile.mkdtemp()
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
bad = 0
try:
    for mode in ('same', 'fat2s'):
        d = tempfile.mkdtemp(dir=T); p = d + '/x.rvt'; shutil.copy(RTE, p)
        if mode == 'fat2s': t = (os.stat(p).st_mtime_ns // 2_000_000_000) * 2_000_000_000; os.utime(p, ns=(t, t))
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', p)
        nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
        st = os.stat(p); b = bytearray(open(p, 'rb').read()); b[-1] ^= 0xFF; open(p, 'wb').write(bytes(b)); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        assert os.stat(p).st_size == st.st_size and os.stat(p).st_mtime_ns == st.st_mtime_ns
        h = sha(p)
        try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'ACCEPTED'
        except Exception as e: res = 'refused ' + type(e).__name__
        ok = res != 'ACCEPTED' and sha(p) == h and os.listdir(d) == ['x.rvt']
        print(mode, res, 'untouched=%s' % (sha(p) == h), os.listdir(d)); bad += not ok
    assert not bad; print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
