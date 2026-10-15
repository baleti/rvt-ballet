"""per-element material sets vs Revit (gt_mat FMAT rows from the oracle): tools/mat_eval.py MODELDIR GT.tsv
For every element with FMAT rows: Revit's set of face materials (Face.MaterialElementId, painted material when painted) vs the viewer's set (elmat table). Prints identical / missing / extra."""
import sys, json, sqlite3, collections, os
def main(md, gt):
    M = json.load(open(os.path.join(md, 'materials.json')))['materials']; db = sqlite3.connect(os.path.join(md, 'model.sqlite'))
    idx = {r[0]: r[1] for r in db.execute('select id, i from el')}
    want = collections.defaultdict(set); kind = {}
    for ln in open(gt, encoding='utf-8', errors='replace'):
        p = ln.rstrip('\n').split('\t')
        if p[0] == 'FMATEL': kind[int(p[1])] = ' '.join(p[2:4])
        if p[0] != 'FMAT': continue
        e = int(p[1].split('.')[0]); kv = dict(x.split('=', 1) for x in p[2:] if '=' in x)
        m = kv.get('paintMaterial') if kv.get('painted') == 'True' and kv.get('paintMaterial') else kv.get('materialId')
        if m and m not in ('-1', ''): want[e].add(int(m))
    name = {m['id']: m['name'] for m in M}; n = ok = 0; rows = []
    for e, w in sorted(want.items()):
        i = idx.get(e)
        have = {M[r[0]]['id'] for r in db.execute('select m from elmat where i=?', (i,))} if i is not None else set()
        n += 1; same = have == w; ok += same
        rows.append('%-5s %-8d %-28s missing=%s extra=%s' % ('OK' if same else 'DIFF', e, kind.get(e, '')[:28], sorted(name.get(x, x) for x in w - have), sorted(name.get(x, x) for x in have - w)))
    print('\n'.join(rows)); print('identical material sets: %d / %d elements' % (ok, n))
if __name__ == '__main__': main(*sys.argv[1:3])
