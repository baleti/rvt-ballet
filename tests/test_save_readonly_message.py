"""RVT: read-only source file and non-writable folder: save_overwrite refuses with a message naming the cause; bytes unchanged."""
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import(); import savegate as sg
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available or os.name == 'nt' or os.geteuid() == 0: print('skip'); return
    for what in ('file', 'folder'):
        wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; shutil.copy(RTE, src); h = hashlib.sha256(open(src, 'rb').read()).hexdigest()
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'ro', 'match': ''})
        os.chmod(src if what == 'file' else wd, 0o444 if what == 'file' else 0o555)
        try:
            try: save.save_overwrite(ss, 'm', src); raise SystemExit('FAIL %s: saved' % what)
            except SystemExit: raise
            except Exception as e: msg = '%s: %s' % (type(e).__name__, e); print(what, '->', msg[:170])
            assert any(w in msg.lower() for w in ('read-only', 'read only', 'not writable', 'permission', 'writable')), msg
            assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h
        finally: os.chmod(wd, 0o755); os.chmod(src, 0o644); ss.close(); shutil.rmtree(wd, True)
    print('rvt readonly OK')
main()
