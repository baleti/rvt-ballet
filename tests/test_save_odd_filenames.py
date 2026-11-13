"""c2x-rvtwrite2 variant: unusual FILE NAMES (non-ASCII, spaces/quotes, 200-char name, newline in name) for in-place SAVE!: accepted with backup equal to the original and only the edit changed, or refused with source intact.
(base doc) SAVE! on (a) a read-only file (0444) in a writable dir, (b) a file in a read-only dir (0555), (c) a 0640 file. Invariant: either refused with the source bytes intact,
or accepted with the file mode preserved (a silent mode change or a silently overwritten read-only file is a finding). Prints what happened."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
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
    names = {'uni': 'Gebäude_建築_Ünïcode ñ.rvt', 'space': "a b  'q' (1) & x;y.rvt", 'long': 'L' * 200 + '.rvt', 'nl': 'line\nbreak.rvt'}
    for name, fn in names.items():
        d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, fn); shutil.copy(RTE, src); h0 = sha(src)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
            save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''})
            save.save_overwrite(ss, 'm', src); res = 'accepted'; ss.close()
        except Exception as e: res = 'refused ' + type(e).__name__ + ' ' + str(e)[:60]
        changed = sha(src) != h0; others = [f for f in os.listdir(d) if f != fn and os.path.isfile(os.path.join(d, f))]; bk = [os.path.join(r, x) for r, _, fs in os.walk(d) for x in fs if x != fn and sha(os.path.join(r, x)) == h0]
        baks = bk if res == 'accepted' else []
        leftovers = [f for f in others if f.endswith(('.tmp', '.part')) or f.startswith('.')]
        ok = (res.startswith('refused') and not changed) or (res == 'accepted' and changed and not leftovers)
        print(name, res, 'changed' if changed else 'intact', 'backups_equal_orig', len(baks), 'leftover', leftovers, 'OK' if ok else 'FINDING'); bad += not ok
    assert not bad
if __name__ == '__main__': main()
