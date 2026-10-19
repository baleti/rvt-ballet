"""software hidden-line renderer (numpy + numba, no browser, runs on host1): tools/hl_soft.py MODELDIR CAMERAS.tsv VIEWID OUT.png [--vg VG3D.json] [--size 2400] [--min-edge 0.01]
Mirrors web/hl.js: glb triangles (three axes, metres), the view's resolved hidden elements / fills / transparency (rvtviewer/vg3d_worker.py JSON), edges = boundary + element change + > 30 deg
(1 mm vertex weld, needle triangles and edges shorter than min-edge dropped) + silhouettes of smooth edges (faces front / back facing, normals oriented away from the element centre).
Orthographic camera from the Revit view (eye, target; feet, Z up -> three x, z, -y), framed on the projected model box (tools/hl_score.py registers scale and shift, so framing does not matter).
Faces occlude (z-buffer); faces of translucent elements do not write depth, lines behind them are drawn faint. Output: grey PNG, black lines on white."""
import sys, os, json, struct, argparse
import numpy as np
from numba import njit
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('model'); ap.add_argument('cameras'); ap.add_argument('view'); ap.add_argument('out')
ap.add_argument('--vg'); ap.add_argument('--eps', type=float, default=3e-4, help='line-vs-face depth tolerance as a fraction of the model depth range'); ap.add_argument('--only', type=int, help='render only this element index (diagnostics)'); ap.add_argument('--opaque', action='store_true', help='ignore view transparency (diagnostics)'); ap.add_argument('--size', type=int, default=2400); ap.add_argument('--min-edge', type=float, default=0.01); ap.add_argument('--angle', type=float, default=30.0)
a = ap.parse_args()
meta = json.load(open(a.model + '/meta.json')); E = meta['elements']
SOFT = {'Planting', 'Entourage', 'Topography'}

# ---------------------------------------------------------------- glb
b = open(a.model + '/model.glb', 'rb').read(); jl, _ = struct.unpack('<II', b[12:20]); J = json.loads(b[20:20 + jl]); BIN = b[20 + jl + 8:]
def acc(i):
    ac = J['accessors'][i]; bv = J['bufferViews'][ac['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[ac['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[ac['componentType']]
    base = bv.get('byteOffset', 0) + ac.get('byteOffset', 0); isz = n * np.dtype(dt).itemsize; stride = bv.get('byteStride') or isz
    if stride == isz: return np.frombuffer(BIN, dt, ac['count'] * n, base).reshape(-1, n)
    return np.stack([np.frombuffer(BIN, dt, n, base + k * stride) for k in range(ac['count'])])
prims = []
for m in J['meshes']:
    for p in m['primitives']:
        at = p['attributes']
        if p.get('mode', 4) != 4 or 'POSITION' not in at or '_EIDX' not in at or 'indices' not in p: continue
        prims.append((acc(at['POSITION']).astype(np.float64), acc(at['_EIDX'])[:, 0].astype(np.int64), acc(p['indices'])[:, 0].astype(np.int64).reshape(-1, 3)))

if a.only is not None: prims = [(P, EI, T[EI[T[:, 0]] == a.only]) for P, EI, T in prims]; prims = [p for p in prims if len(p[2])]
# ---------------------------------------------------------------- view graphics
idx = {int(e[0]): i for i, e in enumerate(E)}; N = len(E)
hidden = np.zeros(N, bool); alpha = np.ones(N); lw = np.ones(N)
if a.vg:
    vg = json.load(open(a.vg))
    for eid in vg['hidden']:
        if eid in idx: hidden[idx[eid]] = True
    for k, v in vg['els'].items():
        if int(k) in idx: alpha[idx[int(k)]] = v[3]; lw[idx[int(k)]] = v[7]
if a.opaque: alpha[:] = 1.0
soft = np.array([e[2] in SOFT for e in E])
_dh = set(meta.get('defaultHidden') or []); hidden |= np.array([e[2] in _dh for e in E])      # categories the viewer hides by default (meta.defaultHidden)

# ---------------------------------------------------------------- camera (three axes)
rows = [l.rstrip('\n').split('\t') for l in open(a.cameras) if l[0] != '#']
row = [r for r in rows if r[0] == a.view][0]; v6 = [float(x) for x in row[2].split() + row[3].split()]
r3 = lambda q: np.array([q[0], q[2], -q[1]]) * 0.3048
eye, tgt = r3(v6[0:3]), r3(v6[3:6]); d = tgt - eye; d /= np.linalg.norm(d)
ref = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.999 else np.array([0.0, 0.0, -1.0])      # straight-down / up views: any horizontal reference
right = np.cross(d, ref); right /= np.linalg.norm(right); up = np.cross(right, d)
view_vec = -d      # towards the eye (orthographic)

# ---------------------------------------------------------------- edges
EDGES = []        # (p0, p1, elem, kind, n1, n2)
for P, EI, T in prims:
    keep_t = ~hidden[EI[T[:, 0]]]
    if not keep_t.any(): continue
    q = np.round(P * 1000).astype(np.int64); _, w = np.unique(q, axis=0, return_inverse=True); w = w.reshape(-1)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]; cr = np.cross(B - A, C - A); l = np.linalg.norm(cr, axis=1); Nn = cr / np.maximum(l, 1e-30)[:, None]
    me = np.maximum.reduce([((B - A) ** 2).sum(1), ((C - A) ** 2).sum(1), ((C - B) ** 2).sum(1)]); sliver = l < 2e-4 * me
    te = EI[T[:, 0]]; ue, inv = np.unique(te, return_inverse=True); cen_u = np.zeros((len(ue), 3)); cnt_u = np.zeros(len(ue))      # element centres, only for the elements of this primitive
    cc = (A + B + C) / 3; np.add.at(cen_u, inv, cc); np.add.at(cnt_u, inv, 1); cen_u /= cnt_u[:, None]
    ks, ts, vs = [], [], []
    for k in range(3):
        va, vb = T[:, k], T[:, (k + 1) % 3]; ok = (w[va] != w[vb]) & keep_t
        lo = np.minimum(w[va], w[vb])[ok]; hi = np.maximum(w[va], w[vb])[ok]
        ks.append(lo.astype(np.int64) * (1 << 26) + hi); ts.append(np.where(ok)[0]); vs.append(np.stack([va[ok], vb[ok]], 1))
    if os.environ.get('HL_DEBUG'): print('prim tris', len(T), 'elements', np.unique(te)[:5])
    keys = np.concatenate(ks); tri = np.concatenate(ts); vv = np.concatenate(vs); o = np.argsort(keys, kind='stable'); keys, tri, vv = keys[o], tri[o], vv[o]
    uniq, start, cnt = np.unique(keys, return_index=True, return_counts=True)
    p0 = P[vv[start, 0]]; p1 = P[vv[start, 1]]; ln = np.linalg.norm(p1 - p0, axis=1); tA = tri[start]; tB = tri[np.minimum(start + 1, len(tri) - 1)]
    two = cnt == 2; el = te[tA]; cosT = np.cos(np.radians(a.angle)); cosS = np.cos(np.radians(2.0))
    dd = np.abs((Nn[tA] * Nn[tB]).sum(1)); same = te[tA] == te[tB]
    long_ = ln >= a.min_edge
    # classes
    bnd = ~two & long_
    elem = two & ~same & long_ & ~sliver[tA] & ~sliver[tB]
    sharp = two & same & (dd < cosT) & long_ & ~sliver[tA] & ~sliver[tB]
    smooth = two & same & (dd >= cosT) & (dd <= cosS) & long_ & ~sliver[tA] & ~sliver[tB]
    # oriented normals for conditional edges
    mid = (p0 + p1) / 2; n1 = Nn[tA].copy(); n2 = Nn[tB].copy(); flip2 = (n1 * n2).sum(1) < 0; n2[flip2] *= -1
    out_ = ((mid - cen_u[np.searchsorted(ue, el)]) * n1).sum(1) < 0; n1[out_] *= -1; n2[out_] *= -1
    if os.environ.get('HL_DEBUG'): print('classes: boundary', int(bnd.sum()), 'elem', int(elem.sum()), 'sharp', int(sharp.sum()), 'smooth', int(smooth.sum()), 'dd min/max', float(dd[two].min()) if two.any() else None, float(dd[two].max()) if two.any() else None)
    softe = soft[el]
    always = bnd | elem | (sharp & ~softe)
    cond = smooth | (sharp & softe)
    sel = always | cond
    kind = np.where(cond[sel], 1, 0)
    EDGES.append((p0[sel], p1[sel], el[sel], kind, n1[sel], n2[sel]))
P0 = np.concatenate([e[0] for e in EDGES]); P1 = np.concatenate([e[1] for e in EDGES]); EL = np.concatenate([e[2] for e in EDGES]); KD = np.concatenate([e[3] for e in EDGES])
N1 = np.concatenate([e[4] for e in EDGES]); N2 = np.concatenate([e[5] for e in EDGES])
sil = (N1 @ view_vec) * (N2 @ view_vec) < 0
if os.environ.get('HL_DEBUG'): print('conditional edges', int((KD == 1).sum()), 'silhouettes', int(sil[KD == 1].sum()), 'view_vec', view_vec, 'sample n1.v', (N1[KD == 1] @ view_vec)[:6], 'n2.v', (N2[KD == 1] @ view_vec)[:6])
drawn = (KD == 0) | sil
P0, P1, EL = P0[drawn], P1[drawn], EL[drawn]

# ---------------------------------------------------------------- project + rasterise
B = meta['bbox']; bb = np.array([[x, z, -y] for x in (B[0][0], B[1][0]) for y in (B[0][1], B[1][1]) for z in (B[0][2], B[1][2])])      # frame on meta's model box (stray huge elements must not shrink the view)
xs = bb @ right; ys = bb @ up
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); S = a.size / max(x1 - x0, y1 - y0) * 0.9; W = int((x1 - x0) * S + a.size * 0.1); H = int((y1 - y0) * S + a.size * 0.1)
def proj(Pp): return np.stack([(Pp @ right - x0) * S + a.size * 0.05, (y1 - Pp @ up) * S + a.size * 0.05, Pp @ d], 1)

@njit(cache=True)
def raster(tx, ty, tz, tal, W, H, zb, ab):
    for t in range(tx.shape[0]):
        x0, x1, x2 = tx[t, 0], tx[t, 1], tx[t, 2]; y0, y1, y2 = ty[t, 0], ty[t, 1], ty[t, 2]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12: continue
        xa = max(int(np.floor(min(x0, x1, x2))), 0); xb = min(int(np.ceil(max(x0, x1, x2))), W - 1); ya = max(int(np.floor(min(y0, y1, y2))), 0); yb = min(int(np.ceil(max(y0, y1, y2))), H - 1)
        for yy in range(ya, yb + 1):
            py = yy + 0.5
            for xx in range(xa, xb + 1):
                px = xx + 0.5; u = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / den; v = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / den; w = 1.0 - u - v
                if u < -1e-9 or v < -1e-9 or w < -1e-9: continue
                z = u * tz[t, 0] + v * tz[t, 1] + w * tz[t, 2]
                if z < zb[yy, xx]:
                    zb[yy, xx] = z; ab[yy, xx] = tal[t]

@njit(cache=True)
def lines(px0, py0, pz0, px1, py1, pz1, el, zo, zt, ta, W, H, eps, img, thick):
    for i in range(px0.shape[0]):
        n = int(max(abs(px1[i] - px0[i]), abs(py1[i] - py0[i]))) + 1
        for s in range(n + 1):
            f = s / n; x = int(np.floor(px0[i] + (px1[i] - px0[i]) * f)); y = int(np.floor(py0[i] + (py1[i] - py0[i]) * f)); z = pz0[i] + (pz1[i] - pz0[i]) * f
            if x < 0 or y < 0 or x >= W or y >= H: continue
            if z > zo[y, x] + eps: continue
            val = 0
            if z > zt[y, x] + eps: val = int(255 * ta[y, x])      # behind a translucent face: faint
            for dx in range(thick[i] + 1):
                for dy in range(thick[i] + 1):
                    xx = x + dx; yy = y + dy
                    if xx < W and yy < H and val < img[yy, xx]: img[yy, xx] = val

zo = np.full((H, W), 1e30); zt = np.full((H, W), 1e30); ta = np.ones((H, W)); ao = np.ones((H, W))
for Pp, EI, T in prims:
    te = EI[T[:, 0]]; ok = ~hidden[te]; opaque = ok & (alpha[te] >= 0.99); trans = ok & ~opaque
    for sel, zb, ab in ((opaque, zo, ao), (trans, zt, ta)):
        if not sel.any(): continue
        Q = proj(Pp); tt = T[sel]; tal = alpha[te[sel]]
        raster(np.ascontiguousarray(Q[tt, 0]), np.ascontiguousarray(Q[tt, 1]), np.ascontiguousarray(Q[tt, 2]), np.ascontiguousarray(tal), W, H, zb, ab)
# translucent faces in front of the opaque ones fade the lines behind them: ta holds the opacity of the nearest translucent face (single value per view: mean alpha of translucent elements)
from scipy.ndimage import maximum_filter
zo = maximum_filter(zo, size=3); zt = maximum_filter(zt, size=3)      # silhouette edges lie where the surface is edge-on: its depth changes by a lot within a pixel, so occlusion is tested against the farthest depth of the 3x3 neighbourhood (the browser's polygonOffset slope factor)
img = np.full((H, W), 255, np.uint8)
Q0, Q1 = proj(P0), proj(P1); eps = np.ptp(bb @ d) * a.eps
thick = (lw[EL] >= 0.8).astype(np.int64)
lines(Q0[:, 0], Q0[:, 1], Q0[:, 2], Q1[:, 0], Q1[:, 1], Q1[:, 2], EL, zo, zt, ta, W, H, eps, img, thick)
Image.fromarray(img).save(a.out); print('wrote', a.out, img.shape, 'edges', len(P0), 'tris', sum(len(p[2]) for p in prims))
