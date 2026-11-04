"""RVT: stale .sgtmp leftovers beside the target (own garbage temp, another document's temp, a user file) do not break an in-place SAVE!: file valid afterwards, own temp swept, foreign ones kept. Synthetic 2024 test file."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
def main():
    if not os.path.exists(RTE): print('SKIP no template'); return
    from rvtballet import save
    save._import()
    import savegate as sg
    from savegate import atomic
    d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; shutil.copy(RTE, src); orig = open(src, 'rb').read()
    mine = d + '/' + atomic._temp_prefix(src) + 'abc123.sgtmp'; other = d + '/' + atomic._temp_prefix(d + '/o.rvt') + 'qqq111.sgtmp'; user = d + '/n.sgtmp'
    for f, b in ((mine, b'garbage'), (other, b'other'), (user, b'user')): open(f, 'wb').write(b)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
    save.save_overwrite(ss, 'm', src); ss.close()
    assert not os.path.exists(mine), 'own stale temp kept'
    assert open(other, 'rb').read() == b'other' and open(user, 'rb').read() == b'user', 'foreign file touched'
    out = open(src, 'rb').read(); assert out[:8] == orig[:8] and len(out) > 100000, 'output looks wrong'
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); ss.close()      # reloads
    print('OK')
if __name__ == '__main__': main()
