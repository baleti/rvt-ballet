"""tools/eval_collect_gt4.py GT_TSV RVT [query...]: fastquery.collect vs the Revit API dump (gt4: E id class 'Category|id' name type_id level_id inst|type uid).
Per query: ids Revit has / we have / both, and on the common ids: name, type id, level id, category id agreement. Prints one line per query."""
import sys, os, collections, time
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
from rvtballet import fastquery as Q
VIEWS = {'View', 'ViewPlan', 'ViewSection', 'View3D', 'ViewSheet', 'ViewSchedule', 'ViewDrafting', 'TableView', 'PanelScheduleView'}
QUERIES = {'Wall': {'Wall'}, 'WallType': {'WallType'}, 'Level': {'Level'}, 'Grid': {'Grid'}, 'View': VIEWS, 'Floor': {'Floor'}, 'FloorType': {'FloorType'},
           'Ceiling': {'Ceiling'}, 'RoofBase': {'FootPrintRoof', 'ExtrusionRoof', 'RoofBase'}, 'Stairs': {'Stairs'}, 'Railing': {'Railing'}, 'Room': {'Room'},
           'FamilyInstance': {'FamilyInstance'}, 'FamilySymbol': {'FamilySymbol'}, 'Family': {'Family'}, 'Material': {'Material'}, 'TextNote': {'TextNote'},
           'Dimension': {'Dimension', 'SpotDimension'}, 'Revision': {'Revision'}, 'RevitLinkInstance': {'RevitLinkInstance'}}
gt, rvt = sys.argv[1], sys.argv[2]; qs = sys.argv[3:] or list(QUERIES)
E = {}
for l in open(gt, encoding='utf-8', errors='replace'):
    if not l.startswith('E\t'): continue
    p = l.rstrip('\n').split('\t')
    if len(p) < 8: continue
    try: cat = int(p[3].rsplit('|', 1)[1]) if '|' in p[3] else None
    except ValueError: cat = None
    E[int(p[1])] = dict(cls=p[2], cat=cat, name=p[4], type=int(p[5]) if p[5].lstrip('-').isdigit() else -1, level=int(p[6]) if p[6].lstrip('-').isdigit() else -1)
for q in qs:
    g = {e: v for e, v in E.items() if v['cls'] in QUERIES[q]}
    t0 = time.time()
    try: rows = Q.collect(rvt, q, workers=int(os.environ.get('W', '6')))
    except Exception as ex: print('%-16s ERROR %s' % (q, ex)); continue
    dt = time.time() - t0; ours = {r['id']: r for r in rows}; both = set(g) & set(ours)
    def agree(f):
        n = ok = 0
        for e in both:
            a = g[e]; b = ours[e]
            if f == 'name': x, y = a['name'], b['name'] or ''
            elif f == 'type': x, y = a['type'], b['type_id'] if b['type_id'] is not None else -1
            elif f == 'level': x, y = a['level'], b['level_id'] if b['level_id'] is not None else -1
            else: x, y = a['cat'], b['category_id']
            n += 1; ok += (x == y)
        return '%d/%d' % (ok, n)
    print('%-16s revit %5d ours %5d both %5d | name %s type %s level %s cat %s | %.1fs' % (q, len(g), len(ours), len(both), agree('name'), agree('type'), agree('level'), agree('cat'), dt), flush=True)
