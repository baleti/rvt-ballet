"""c6x-rvtmatrix: a FIFO or /dev/null named *.rvt as the in-place source must be refused (not hang, not replaced by a regular file). Runs the save in a child with a 60 s timeout; a FIFO is opened non-blocking by a keeper so a blocking open cannot be the reason it returns."""
import os, sys, tempfile, shutil, subprocess, json, stat
_T = tempfile.mkdtemp(); HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CH = r'''
import os, sys, json
sys.path.insert(0, %r)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import save
save._import()
import savegate as sg
src = sys.argv[1]
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'param': 'Comments', 'value': 'x'})
save.save_overwrite(ss, 'm', src)
print('ACCEPTED')
''' % HERE
env = dict(os.environ, SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1')
bad = 0
try:
    fifo = _T + '/f.rvt'; os.mkfifo(fifo)
    for name, path in (('fifo', fifo), ('devnull_link', None)):
        if path is None:
            path = _T + '/n.rvt'; os.symlink('/dev/null', path)
        keeper = os.open(fifo, os.O_RDWR | os.O_NONBLOCK) if name == 'fifo' else None
        try:
            r = subprocess.run([sys.executable, '-c', CH, path], env=env, capture_output=True, text=True, timeout=60)
            out = 'ACCEPTED' if 'ACCEPTED' in r.stdout else 'refused rc=%d' % r.returncode
        except subprocess.TimeoutExpired: out = 'HANG'
        finally:
            if keeper is not None: os.close(keeper)
        kind = 'fifo' if stat.S_ISFIFO(os.lstat(fifo).st_mode) else 'other'
        still = (os.path.islink(path) or stat.S_ISFIFO(os.lstat(path).st_mode)) and not os.path.isfile(path) if name == 'fifo' else os.path.islink(path) and os.readlink(path) == '/dev/null'
        print(name, out, 'type preserved' if still else 'REPLACED')
        if out in ('HANG', 'ACCEPTED') or not still: bad += 1
    if bad: print('FAIL', bad); sys.exit(1)
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
