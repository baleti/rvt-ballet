#!/usr/bin/env python3
"""rvt_resave_equiv.py OURS_BASE REVIT_BASE : resave-equivalence oracle (c4x-rvtdiff 155).
Both arguments are the BASE files that tools/rvt_diff_vm.py saved with op 'none' (Revit's own no-op resave) of (a) OUR edited output and (b) the Revit-made edit of the same sample.
If our output is semantically equal to the Revit-made one, Revit's resaves of both carry the same elements: 0 added, 0 removed, 0 changed records. Exit 0 = equivalent, 1 = differences (listed), 2 = tool error."""
import json, os, subprocess, sys, tempfile
def classify(d, tolerate_headers=False):
    """(ok, header_only_ids, body_ids): with tolerate_headers a changed record whose body fields list is empty and whose record length is equal (ElementHeader-only change: session stamps, id list order) does not count (c4x-rvtdiff 157, measured door delete 160/161)"""
    ho, body = [], []
    for c in d.get('changed', []):
        if c.get('header_changed') and not c.get('fields') and not c.get('rec_len', [[], []])[0] and not c.get('rec_len', [[], []])[1]: ho.append(c['id'])
        else: body.append(c['id'])
    ok = not d.get('added') and not d.get('removed') and not body and (tolerate_headers or not ho)
    return ok, ho, body
def field_diff_ids(a, b):
    """ids whose DECODED record fields differ between the two files, independent of rvt_diff's header/record walker (which cannot see instance-body changes such as a Mark string: c4x-rvtdiff 223 retraction)."""
    sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
    import rvt_xcache
    ra, rb = rvt_xcache.get_x_ro(a)['recs'], rvt_xcache.get_x_ro(b)['recs']
    dump = lambda r: json.dumps(r.get('fields'), sort_keys=True, default=str)
    return sorted(k[0] for k in set(ra) & set(rb) if dump(ra[k]) != dump(rb[k]))
def main(a, b, tolerate=False):
    j = os.path.join(tempfile.mkdtemp(), 'd.json')
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_diff.py'), a, b, '--json', j] + ([] if tolerate else ['--nofields']), capture_output=True, text=True)
    if not os.path.exists(j): print('diff tool failed:', r.stderr[-300:]); return 2
    d = json.load(open(j)); ch = [c['id'] for c in d.get('changed', [])]
    print('added %s removed %s changed %d %s' % (d.get('added'), d.get('removed'), len(ch), ch[:20]))
    ok, ho, body = classify(d, tolerate)
    fd = field_diff_ids(a, b); print('decoded-field differences (walker independent): %d %s' % (len(fd), fd[:20]))
    if fd: ok = False; body = sorted(set(body) | set(fd))
    if tolerate: print('header-only changes %s, body changes %s' % (ho[:20], body[:20]))
    print('EQUIVALENT' if ok else 'DIFFERENT'); return 0 if ok else 1
if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if x != '--tolerate-header-only']
    if len(args) != 2: print(__doc__ + '\nOption --tolerate-header-only: ElementHeader-only differences (session stamps, id list order) do not count; any body, added or removed element still does.'); sys.exit(2)
    sys.exit(main(args[0], args[1], '--tolerate-header-only' in sys.argv))
