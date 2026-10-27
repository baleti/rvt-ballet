"""convert many corpus files, one line per file (OK/FAIL + timing); safe to run in background"""
import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import cli
for p in sys.argv[1:]:
    t = time.time()
    try:
        d = cli.ensure(p, False, log=lambda *a: None); print('OK  ', os.path.basename(p), round(time.time() - t), flush=True)
    except Exception as e:
        print('FAIL', os.path.basename(p), repr(e)[:200], flush=True); traceback.print_exc(limit=3)
