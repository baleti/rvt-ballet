#!/usr/bin/env python3
"""rvt_resave_equiv.py OURS_BASE REVIT_BASE : resave-equivalence oracle (c4x-rvtdiff 155).
Both arguments are the BASE files that tools/rvt_diff_vm.py saved with op 'none' (Revit's own no-op resave) of (a) OUR edited output and (b) the Revit-made edit of the same sample.
If our output is semantically equal to the Revit-made one, Revit's resaves of both carry the same elements: 0 added, 0 removed, 0 changed records. Exit 0 = equivalent, 1 = differences (listed), 2 = tool error."""
import json, os, subprocess, sys, tempfile
def main(a, b):
    j = os.path.join(tempfile.mkdtemp(), 'd.json')
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_diff.py'), a, b, '--json', j, '--nofields'], capture_output=True, text=True)
    if not os.path.exists(j): print('diff tool failed:', r.stderr[-300:]); return 2
    d = json.load(open(j)); ch = [c['id'] for c in d.get('changed', [])]
    print('added %s removed %s changed %d %s' % (d.get('added'), d.get('removed'), len(ch), ch[:20]))
    ok = not d.get('added') and not d.get('removed') and not ch
    print('EQUIVALENT' if ok else 'DIFFERENT'); return 0 if ok else 1
if __name__ == '__main__':
    if len(sys.argv) != 3: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
