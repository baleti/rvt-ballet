"""add_edits: one trial replay for a list of edits (add_edit replays all per call, ~20 s each on a 28 MB model). Same recorded ops and same saved bytes as add_edit one by one; a refused op in the list records NOTHING (all or none)."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
OK = {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''}
def main():
    from rvtballet import save
    save._import()
    import savegate as sg
    d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'a.rvt'); shutil.copy(RTE, src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
    try: save.add_edits(ss, 'm', src, [OK, dict(OK, eid=2147000000)]); raise SystemExit('FAIL: bad op accepted')
    except SystemExit: raise
    except Exception: pass
    assert ss.edits('m').ops == [], 'bad list left edits recorded'
    r = save.add_edits(ss, 'm', src, [OK]); assert r['n'] == 1
    a = save.save_as(ss, 'm', src, os.path.join(d, 'b.rvt'))
    ss2 = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss2.doc('m', src); save.add_edit(ss2, 'm', src, OK); save.save_as(ss2, 'm', src, os.path.join(d, 'c.rvt'))
    h = lambda n: hashlib.sha256(open(os.path.join(d, n), 'rb').read()).hexdigest()
    assert h('b.rvt') == h('c.rvt'), 'batch output differs from sequential'
    print('OK')
if __name__ == '__main__': main()
