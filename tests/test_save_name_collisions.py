"""RVT: Revit's own backups (s.0001.rvt ...) and look-alikes of our temp/backup names beside the source survive an in-place SAVE! byte for byte."""
import os, sys, tempfile, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import(); import savegate as sg
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); return
    wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; shutil.copy(RTE, src)
    names = ['s.0001.rvt', 's.0002.rvt', 's.rvt.sgtmp', '.s.rvt.tmp-%d' % os.getpid(), 's.rvt.bak', 's.rvt~', 's.rvt.orig', 's (1).rvt', 's.rvt.lock']
    try:
        for n in names: open(os.path.join(wd, n), 'wb').write(('SENTINEL ' + n).encode())
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'nc', 'match': ''})
        r = save.save_overwrite(ss, 'm', src); ss.close()
        for n in names: assert open(os.path.join(wd, n), 'rb').read() == ('SENTINEL ' + n).encode(), n
        print('rvt name collisions OK')
    finally: shutil.rmtree(wd, True)
main()
