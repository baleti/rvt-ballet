"""c6x-rvtwrite items 24+25: (a) the source is changed by a foreign writer WHILE SAVE! is verifying (after the first check, before the rename): same-size flip with mtime restored, a size-changing append, and a byte change with new mtime. SAVE! must refuse (Conflict), keep the foreign bytes, leave no temp/backup debris.
(b) Revit worksharing/backup sidecars (s.0001.rvt, s.rvt.lock, s.0001.rte) sit beside the file: SAVE! succeeds and the sidecars stay byte-identical."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def flip(p):
    st = os.stat(p); b = bytearray(open(p, 'rb').read()); b[len(b) // 2] ^= 0x01; open(p, 'wb').write(b); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
def append(p): open(p, 'ab').write(b'\0' * 17)
def touch(p):
    b = open(p, 'rb').read(); open(p, 'wb').write(b[:-1] + bytes([b[-1] ^ 1]))
SNEAKS = (('flip_same_mtime', flip), ('append', append), ('byte_change_new_mtime', touch))
def main():
    from rvtballet import save
    save._import()
    import savegate as sg, savegate.core as core
    orig = core._produce
    for name, fn in SNEAKS:
        d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        def hooked(*a, **k):
            r = orig(*a, **k); fn(src); return r
        core._produce = hooked
        try:
            try: save.save_overwrite(ss, 'm', src); raise SystemExit('ESCAPE: change during verify overwritten (%s)' % name)
            except SystemExit: raise
            except Exception as e: assert type(e).__name__ == 'Conflict', (name, type(e).__name__, e); print(name, 'refused', type(e).__name__)
        finally: core._produce = orig
        left = sorted(os.listdir(d)); assert left == ['s.rvt'], ('debris', name, left)
        ss.close()
    d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src)
    side = {d + '/s.0001.rvt': b'bak1', d + '/s.rvt.lock': b'lock', d + '/s.0001.rte': b'bak2'}
    for p, b in side.items(): open(p, 'wb').write(b)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); save.save_overwrite(ss, 'm', src); ss.close()
    for p, b in side.items(): assert open(p, 'rb').read() == b, ('sidecar modified', p)
    print('OK')
if __name__ == '__main__': main()
