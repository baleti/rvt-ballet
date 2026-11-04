"""RVT: in-place SAVE! of the same 2024 test file on /dev/shm (tmpfs, cache on the root disk) and on the root disk gives byte-identical output, no .sgtmp left. Skips without /dev/shm or template."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
def main():
    if not os.path.exists(RTE) or not os.access('/dev/shm', os.W_OK): print('SKIP'); return
    from rvtballet import save
    save._import()
    import savegate as sg
    shm = tempfile.mkdtemp(dir='/dev/shm'); disk = tempfile.mkdtemp(dir=_T)
    if os.stat(shm).st_dev == os.stat(disk).st_dev: print('SKIP same fs'); return
    outs = []
    try:
        for base in (disk, shm):
            src = base + '/s.rvt'; shutil.copy(RTE, src)
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); save.save_overwrite(ss, 'm', src); ss.close()
            assert not [f for f in os.listdir(base) if f.endswith('.sgtmp')], 'temp left in ' + base
            outs.append(hashlib.sha256(open(src, 'rb').read()).hexdigest())
    finally: shutil.rmtree(shm, True)
    assert outs[0] == outs[1], 'tmpfs save differs from disk save'
    print('OK')
if __name__ == '__main__': main()
