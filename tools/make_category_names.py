"""Build rvtviewer/data/category_names.json from Revit-produced ground-truth dumps (gt4/*.tsv: 'E id class Name|BuiltInCategoryId ...').
Provenance: Revit API output only. No ODA-derived tables."""
import glob, json, os, sys
gt = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/rvt-research/gt4')
out = {}
for f in glob.glob(gt + '/*.tsv'):
    for l in open(f, errors='ignore'):
        if l.startswith('E\t'):
            x = l.rstrip('\n').split('\t')
            if len(x) > 3 and '|' in x[3]:
                n, i = x[3].rsplit('|', 1)
                out.setdefault(i, n.split('|')[0])
json.dump(out, open(os.path.join(os.path.dirname(__file__), '..', 'rvtviewer', 'data', 'category_names.json'), 'w'), indent=0, sort_keys=True)
print(len(out), 'categories')
