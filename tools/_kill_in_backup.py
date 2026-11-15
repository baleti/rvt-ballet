"""wrapper: SIGKILL this process midway through the savegate backup copy (the .part file is half written), then run the in-place delete tool. usage: _kill_in_backup.py FILE"""
import os, sys, signal, runpy, shutil
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
from savegate import backup
_orig = shutil.copyfileobj
def _cp(a, b, n=1 << 20):
    b.write(a.read(1 << 20)); b.flush(); os.kill(os.getpid(), signal.SIGKILL)
backup.shutil = type('S', (), {'copyfileobj': staticmethod(_cp)})
sys.argv = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_inplace_delete.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
