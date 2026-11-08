"""c7x-rvtmatrix: SAVE! and SAVE AS on file names a real office has: spaces, unicode (umlaut, CJK), leading dot, '#', '&', '%', quotes, 200-char name, name with two dots and no .rvt case.
Invariant: accepted with the right bytes and a working backup restore, or refused with the source intact; never a stray file with a mangled name."""
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
NAMES = ['plain name with spaces.rvt', 'Büro Ärger 日本語.rvt', '.hidden.rvt', "a#b&c%d'e\"f.rvt", 'x' * 190 + '.rvt', 'two.dots.in.name.v2.rvt', 'UPPER.RVT']
def main():
    from rvtballet import save
    save._import()
    import savegate as sg
    bad = 0
    for n in NAMES:
        d = tempfile.mkdtemp(dir=_T, suffix=' dir with space'); src = os.path.join(d, n); shutil.copy(RTE, src); h0 = sha(src); before = set(os.listdir(d))
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''})
        try:
            dest = os.path.join(d, 'copy of ' + n); save.save_as(ss, 'm', src, dest); r = save.save_overwrite(ss, 'm', src)
            ok = sha(src) != h0 and sha(src) == sha(dest) and bool(r['backup'])
            save.restore_backup(ss, 'm', src, 0); ok = ok and sha(src) == h0; res = 'accepted'
        except Exception as e: ok = sha(src) == h0; res = 'refused ' + type(e).__name__ + str(e)[:80]
        extra = set(os.listdir(d)) - before - {os.path.basename(dest), '.savegate'}; ok = ok and not extra
        print(repr(n[:24]), res, 'OK' if ok else 'FINDING %s' % extra); bad += not ok; ss.close()
    assert not bad
if __name__ == '__main__': main()
