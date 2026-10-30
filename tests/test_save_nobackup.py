"""c7x-rvtmatrix: SAVE! when NO backup store can be written (the .savegate dir is blocked by a regular file and the cache store dir is blocked too). Invariant: refused, source
bytes intact, no temp left; the same edit with a working store succeeds and its backup restores the original sha256 (no in-place overwrite without a way back)."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def main():
    from rvtballet import save
    save._import()
    import savegate as sg
    EDIT = {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''}
    d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src)
    open(d + '/.savegate', 'w').write('blocker'); open(_T + '/blockfile', 'w').write('blocker'); os.environ['SAVEGATE_CACHE'] = _T + '/blockfile'
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); save.add_edit(ss, 'm', src, EDIT)
    try: save.save_overwrite(ss, 'm', src); raise SystemExit('ESCAPE: overwritten without any backup store')
    except SystemExit: raise
    except Exception as e: print('no store ->', type(e).__name__, str(e)[:100])
    assert sha(src) == h0, 'source changed'; left = [f for f in os.listdir(d) if 'sgtmp' in f or f.endswith('.part')]; assert not left, left; ss.close()
    os.remove(d + '/.savegate'); os.environ['SAVEGATE_CACHE'] = _T + '/c'
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); save.add_edit(ss, 'm', src, EDIT)
    r = save.save_overwrite(ss, 'm', src); assert r['backup'] and sha(src) != h0
    save.restore_backup(ss, 'm', src, 0); assert sha(src) == h0, 'restore did not return the original'; print('OK')
if __name__ == '__main__': main()
