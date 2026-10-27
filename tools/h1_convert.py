"""host1 conversion (h1run, env occ or rvt, no .venv): tools/h1_convert.py FILE.rvt OUTDIR"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import build
m = build.convert(sys.argv[1], os.path.expanduser(sys.argv[2]), log=print); print('done', m.get('coverage') and len(m['coverage']))
