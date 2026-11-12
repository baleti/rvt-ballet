"""rvt_elemhash_compare.py A.txt B.txt [id,id,...]: compare two rvt_elemhash_readback outputs. Prints counts, the number of elements whose Revit-side hash differs and whether ALL differing ids are in the allowed list (the edited elements + declared dependents). Exit 0 when only allowed ids differ and no element is missing/added."""
import sys, re
def load(p):
    d = {}
    for l in open(p):
        m = re.match(r'EH (\d+) ([0-9a-f]{8})', l)
        if m: d[int(m.group(1))] = m.group(2)
    return d
a, b = load(sys.argv[1]), load(sys.argv[2]); allowed = {int(x) for x in sys.argv[3].split(',')} if len(sys.argv) > 3 and sys.argv[3] else set()
diff = {k for k in a.keys() & b.keys() if a[k] != b[k]}; only_a = set(a) - set(b); only_b = set(b) - set(a)
print('elements A %d B %d; differing %d; only-in-A %d; only-in-B %d' % (len(a), len(b), len(diff), len(only_a), len(only_b)))
bad = diff - allowed
print('differing ids outside the allowed list: %d' % len(bad), sorted(bad)[:10])
print('untouched elements identical in Revit view: %.4f %%' % (100.0 * (len(a.keys() & b.keys()) - len(diff)) / max(1, len(a.keys() & b.keys()))))
sys.exit(0 if not bad and not only_a and not only_b and a and b else 1)
