"""c7x-rvtmatrix: SAVE! on (a) a read-only file (0444) in a writable dir, (b) a file in a read-only dir (0555), (c) a 0640 file. Invariant: either refused with the source bytes intact,
or accepted with the file mode preserved (a silent mode change or a silently overwritten read-only file is a finding). Prints what happened."""
import os, sys, tempfile, shutil, hashlib, stat
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def main():
    from rvtballet import save
    save._import()
    import savegate as sg
    bad = 0
    for name, fmode, dmode in (('ro_file', 0o444, 0o755), ('ro_dir', 0o644, 0o555), ('mode640', 0o640, 0o755)):
        d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src); os.chmod(src, fmode); os.chmod(d, dmode)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''})
        try: save.save_overwrite(ss, 'm', src); res = 'accepted'
        except Exception as e: res = 'refused ' + type(e).__name__
        os.chmod(d, 0o755); m = stat.S_IMODE(os.stat(src).st_mode); changed = sha(src) != h0
        ok = (res.startswith('refused') and not changed) or (res == 'accepted' and m == fmode and name != 'ro_file' and name != 'ro_dir')
        print(name, res, 'mode %o -> %o' % (fmode, m), 'bytes changed' if changed else 'bytes intact', 'OK' if ok else 'FINDING'); bad += not ok; ss.close()
    assert not bad
if __name__ == '__main__': main()
