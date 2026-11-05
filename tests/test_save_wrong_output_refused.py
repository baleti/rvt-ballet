"""ESCAPE guard (RVT in place): if the writer produced a DIFFERENT edit than requested (other string value / other element), the element-level gate must refuse and the source stays byte-identical."""
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def session(src):
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); return ss
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); return
    wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; alt = wd + '/alt.rvt'; shutil.copy(RTE, src); shutil.copy(RTE, alt); h = sha(src)
    try:
        # the 'wrong' output: same element, other value
        s2 = session(alt); save.add_edit(s2, 'm', alt, {'op': 'set_string', 'eid': 24, 'value': 'WRONG', 'match': ''}); d2 = s2.doc('m', alt); wrong = save._pending(s2, 'm', d2, None, None)[0]; s2.close()
        ss = session(src); save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'asked', 'match': ''})
        import rvtballet.edit as E
        real = E.apply_full; E.apply_full = lambda buf, ops: (wrong, real(buf, ops)[1])      # only the writer is replaced: the read-back inside _pending stays in place
        refused = None
        try: save.save_overwrite(ss, 'm', src)
        except Exception as e: refused = '%s: %s' % (type(e).__name__, str(e)[:120])
        finally: E.apply_full = real
        print('wrong output ->', refused)
        assert refused, 'ESCAPE: a writer output with another value than requested was written'
        assert sha(src) == h, 'source changed'
        ss.close(); print('wrong output refused OK')
    finally: shutil.rmtree(wd, True)
main()
