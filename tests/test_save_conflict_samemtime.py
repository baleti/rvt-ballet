"""c7x-rvtmatrix: the source is changed behind the viewer's back with SAME size and SAME mtime (one byte flipped, os.utime restored), once before the first save and once
after a first successful SAVE!. SAVE! must refuse (Conflict, 409) and leave the foreign bytes untouched; a size-only or mtime-only check would overwrite it."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def sneak(p):
    st = os.stat(p); b = bytearray(open(p, 'rb').read()); b[len(b) // 2] ^= 0x01; open(p, 'wb').write(b); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    s2 = os.stat(p); assert (s2.st_size, s2.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
def main():
    from rvtballet import save
    save._import()
    import savegate as sg
    for first_save in (False, True):
        d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        if first_save: save.save_overwrite(ss, 'm', src)
        sneak(src); h1 = sha(src)
        try: save.save_overwrite(ss, 'm', src); raise SystemExit('ESCAPE: foreign change overwritten (first_save=%s)' % first_save)
        except SystemExit: raise
        except Exception as e: print('first_save', first_save, 'refused', type(e).__name__); assert type(e).__name__ == 'Conflict', e
        assert sha(src) == h1, 'foreign bytes modified'; ss.close()
    print('OK')
if __name__ == '__main__': main()
