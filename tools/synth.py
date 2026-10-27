"""Synthetic 150k-element model (random boxes + ducts) to stress-test loading and navigation. Not derived from any Revit file."""
import os, sys, json, sqlite3, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import glb, geom, build
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150000
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(1)
cats = ['Walls', 'Floors', 'Ducts', 'Pipes', 'Structural Framing', 'Furniture', 'Doors', 'Windows', 'Lighting Fixtures', 'Air Terminals']
acc = {c: {'pos': [], 'idx': [], 'eidx': [], 'ranges': [], 'nv': 0, 'nt': 0} for c in cats}
els = []
for i in range(N):
    c = cats[i % len(cats)]; lo = rng.uniform([0, 0, 0], [300, 200, 60]); sz = rng.uniform(0.3, 6, 3) if c not in ('Ducts', 'Pipes') else np.array([rng.uniform(3, 20), 1, 1])
    m = geom.box(lo, lo + sz); a = acc[c]
    a['pos'].append(m.v); a['idx'].append(m.f.reshape(-1) + a['nv']); a['eidx'].append(np.full(len(m.v), i, np.float32)); a['ranges'] += [i, a['nt'], len(m.f)]; a['nv'] += len(m.v); a['nt'] += len(m.f)
    els.append([1000 + i, 'FamilyInstance', c, 'Elem %d' % i, 'Type %d' % (i % 40), 'Level %d' % (i % 12), 'bbox', False])
batches = []; bm = []
for c, a in acc.items():
    col = build.cat_color(c)
    batches.append({'name': c, 'color': (*col, 1.0), 'pos': glb.to_yup_m(np.vstack(a['pos'])), 'eidx': np.concatenate(a['eidx']), 'idx': np.concatenate(a['idx']).astype(np.uint32)})
    bm.append({'cat': c, 'kind': 'tri', 'color': '#808080', 'alpha': 1, 'ranges': a['ranges'], 'tris': a['nt']})
t = time.time(); glb.write_glb(os.path.join(out, 'model.glb'), batches); print('glb', round(time.time() - t, 1), os.path.getsize(os.path.join(out, 'model.glb')) // 1e6, 'MB')
meta = {'file': 'synthetic', 'levels': [{'id': k, 'name': 'Level %d' % k, 'elev': k * 5.0} for k in range(12)], 'grids': [], 'batches': bm, 'rooms': [], 'views': [], 'sheets': [], 'bbox': [[0, 0, 0], [300, 200, 60]],
        'fidLabels': build.FID_LABEL, 'defaultHidden': [], 'elements': els, 'coverage': {c: {'bbox': N // len(cats)} for c in cats}, 'bboxAgreement': {}}
json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), separators=(',', ':'))
db = sqlite3.connect(os.path.join(out, 'model.sqlite')); db.executescript('drop table if exists el;drop table if exists prm;create table el(i integer primary key, id integer, cls text, cat text, name text, type text, family text, level text, uid text, ifc text, fid text, bb text, iou real);create table prm(i integer, k text, v text);create index prm_i on prm(i);')
db.executemany('insert into el values(?,?,?,?,?,?,?,?,?,?,?,?,?)', [(i, e[0], e[1], e[2], e[3], e[4], 'Family', e[5], None, None, 'bbox', None, None) for i, e in enumerate(els)])
db.executemany('insert into prm values(?,?,?)', [(i, 'Mark', str(i)) for i in range(N)]); db.commit()
