"""list the elements whose volume ratio vs the Revit oracle is off: tools/oracle_bad.py CORPUS_FILE [CLASS] -> id, class, name, family/type, ratio, IoU, fidelity (converts fresh into a work dir, one process)"""
import sys, os, json, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import compare_gt; from rvtviewer import build
src = sys.argv[1]; cls = sys.argv[2] if len(sys.argv) > 2 else 'FamilyInstance'; out = os.path.expanduser('~/.cache/rvt-viewer/oracle-bad'); shutil.rmtree(out, ignore_errors=True)
build.convert(src, out, log=lambda *a: None); compare_gt.main(out, os.path.expanduser('~/rvt-research/gt_geom'))
m = json.load(open(out + '/meta.json'))['elements']; c = json.load(open(out + '/compare.json'))['elements']
rows = [(v.get('vratio'), int(i), v) for i, v in c.items() if m[int(i)][1] == cls and v.get('vratio') and abs(v['vratio'] - 1) > .02]
print(len(rows), 'bad of', sum(1 for i in c if m[int(i)][1] == cls))
for r, i, v in sorted(rows, key=lambda x: x[0])[:60]: print(m[i][0], m[i][1], '|', m[i][2], '|', m[i][3], '| ratio', r, 'iou', v.get('iou'), v.get('fid'), 'area', v.get('aratio'))
