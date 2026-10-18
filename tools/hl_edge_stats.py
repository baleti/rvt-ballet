"""edge statistics of a converted model (numpy, no browser): tools/hl_edge_stats.py MODELDIR [N]
Re-implements the web/hl.js edge extractor (1 mm vertex weld, boundary / element-change / >30 deg edges, needle triangles) per glb primitive and reports, per element (the _EIDX attribute indexes meta.json elements),
how many sharp edges are short (< 1 cm, < 5 cm), how many triangles are needles, and the top N offenders with their category / type: where the specks of the hidden-line style come from."""
import sys, os, json, struct, collections
import numpy as np
mdir = sys.argv[1]; top = int(sys.argv[2]) if len(sys.argv) > 2 else 15
meta = json.load(open(mdir + '/meta.json')); E = meta['elements']
b = open(mdir + '/model.glb', 'rb').read(); jl, _ = struct.unpack('<II', b[12:20]); J = json.loads(b[20:20 + jl]); off = 20 + jl + 8; BIN = b[off:]
def acc(i):
    a = J['accessors'][i]; bv = J['bufferViews'][a['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a['componentType']]
    base = bv.get('byteOffset', 0) + a.get('byteOffset', 0); stride = bv.get('byteStride') or n * np.dtype(dt).itemsize
    if stride == n * np.dtype(dt).itemsize: return np.frombuffer(BIN, dt, a['count'] * n, base).reshape(-1, n)
    return np.stack([np.frombuffer(BIN, dt, n, base + k * stride) for k in range(a['count'])])
stat = collections.defaultdict(lambda: collections.Counter()); total = collections.Counter()
for m in J['meshes']:
    for p in m['primitives']:
        at = p['attributes']
        if p.get('mode', 4) != 4 or 'POSITION' not in at or '_EIDX' not in at or 'indices' not in p: continue
        P = acc(at['POSITION']).astype(np.float64); EI = acc(at['_EIDX'])[:, 0].astype(np.int64); T = acc(p['indices'])[:, 0].astype(np.int64).reshape(-1, 3)
        q = np.round(P * 1000).astype(np.int64); _, w = np.unique(q, axis=0, return_inverse=True); w = w.reshape(-1)
        a, b2, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]; cr = np.cross(b2 - a, c - a); l = np.linalg.norm(cr, axis=1); N = cr / np.maximum(l, 1e-30)[:, None]
        me = np.maximum.reduce([((b2 - a) ** 2).sum(1), ((c - a) ** 2).sum(1), ((c - b2) ** 2).sum(1)]); sliver = l < 2e-4 * me
        te = EI[T[:, 0]]
        for t in np.where(sliver)[0]: stat[te[t]]['needle'] += 1
        keys = []; tri = []
        for k in range(3):
            va, vb = T[:, k], T[:, (k + 1) % 3]; a_, b_ = w[va], w[vb]; ok = a_ != b_
            lo, hi = np.minimum(a_, b_)[ok], np.maximum(a_, b_)[ok]; keys.append(lo.astype(np.int64) * (1 << 26) + hi); tri.append(np.where(ok)[0]); 
        keys = np.concatenate(keys); tri = np.concatenate(tri); order = np.argsort(keys, kind='stable'); keys = keys[order]; tri = tri[order]
        uniq, start, cnt = np.unique(keys, return_index=True, return_counts=True)
        # length per unique edge (from the first occurrence's vertex pair)
        allv = np.concatenate([np.stack([T[:, k], T[:, (k + 1) % 3]], 1)[np.where(w[T[:, k]] != w[T[:, (k + 1) % 3]])[0]] for k in range(3)])[order]
        ln = np.linalg.norm(P[allv[start, 0]] - P[allv[start, 1]], axis=1)
        for u in range(len(uniq)):
            s, n_ = start[u], cnt[u]; A = tri[s]; e = te[A]
            if n_ == 2:
                B = tri[s + 1]
                if sliver[A] or sliver[B]: continue
                if te[B] != e: kind = 'elem'
                else:
                    d = abs(float(N[A] @ N[B]))
                    if d >= np.cos(np.radians(2)): continue
                    kind = 'sharp' if d < np.cos(np.radians(30)) else 'smooth'
            else: kind = 'boundary'
            stat[e][kind] += 1; total[kind] += 1
            if kind in ('sharp', 'boundary'):
                if ln[u] < 0.01: stat[e]['sharp<1cm'] += 1; total['sharp<1cm'] += 1
                elif ln[u] < 0.05: stat[e]['sharp<5cm'] += 1; total['sharp<5cm'] += 1
print('total', dict(total))
rows = sorted(stat.items(), key=lambda kv: -(kv[1]['sharp<1cm'] + kv[1]['sharp<5cm'] + kv[1]['needle']))[:top]
for e, c in rows:
    el = E[e] if e < len(E) else ['?'] * 6
    print('elem %6s %-18s %-22s needle %5d  <1cm %5d  <5cm %5d  sharp %6d  boundary %6d  smooth %6d' % (el[0], str(el[2])[:18], str(el[4])[:22], c['needle'], c['sharp<1cm'], c['sharp<5cm'], c['sharp'], c['boundary'], c['smooth']))
