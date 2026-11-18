"""wrapper: SIGKILL this process at savegate atomic step $KILL_AT (tmp_written|before_replace|after_replace), then run the in-place Mark tool. usage: _kill_at_step.py FILE"""
import os, sys, signal, runpy
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
from savegate import atomic
at = os.environ['KILL_AT']
atomic._hook = lambda name: os.kill(os.getpid(), signal.SIGKILL) if name == at else None
sys.argv = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_inplace_mark.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
