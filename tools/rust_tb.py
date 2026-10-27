"""print the traceback of a Rust fast path failure: tools/rust_tb.py FILE.rvt"""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import build
VF = build.fast_module(); print('fast module', VF)
try:
    fm = VF.open(sys.argv[1]); q = fm.quick(); print('quick ok', q.get('levels'))
    import tempfile; nq = build.write_quick_preview(tempfile.mkdtemp(), q, sys.argv[1]); print('preview ok', nq)
    raw = VF.load(sys.argv[1], print, model=fm); print('load ok')
except BaseException:
    traceback.print_exc()
