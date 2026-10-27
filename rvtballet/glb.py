"""Minimal GLB (glTF 2.0 binary) writer. One mesh node per batch; custom per-vertex attribute _EIDX = element index.
Normals are omitted on purpose (viewer shades flat with screen-space derivatives), which keeps files small."""
import json, struct
import numpy as np

def _lin(c):
    """sRGB 0..1 (Revit colours, category colours) -> linear (glTF baseColorFactor is linear)"""
    c = float(c); return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def to_yup_m(v):
    """Revit feet Z-up -> glTF metres Y-up"""
    v = np.asarray(v, float) * 0.3048
    return np.c_[v[:, 0], v[:, 2], -v[:, 1]]

def write_glb(path, batches, extras=None):
    """batches: list of dict(name, color(r,g,b,a), mode(4 tris|1 lines), pos Nx3 float32 (already y-up m), eidx N float32, idx int32 flat)"""
    bin_parts = []; off = 0; views = []; accs = []; meshes = []; mats = []; nodes = []

    def add(arr, target=None):
        nonlocal off
        b = arr.tobytes(); pad = (-len(b)) % 4
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(b), **({'target': target} if target else {})})
        bin_parts.append(b + b'\0' * pad); off += len(b) + pad
        return len(views) - 1
    for i, b in enumerate(batches):
        pos = np.ascontiguousarray(b['pos'], np.float32); ei = np.ascontiguousarray(b['eidx'], np.float32); ix = np.ascontiguousarray(b['idx'], np.uint32)
        if len(ix) == 0: continue
        lo = pos.min(0).tolist(); hi = pos.max(0).tolist()
        a_pos = len(accs); accs.append({'bufferView': add(pos, 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC3', 'min': lo, 'max': hi})
        a_ei = len(accs); accs.append({'bufferView': add(ei, 34962), 'componentType': 5126, 'count': len(ei), 'type': 'SCALAR'})
        attrs = {'POSITION': a_pos, '_EIDX': a_ei}
        if b.get('mat') is not None:
            a_mt = len(accs); accs.append({'bufferView': add(np.ascontiguousarray(b['mat'], np.float32), 34962), 'componentType': 5126, 'count': len(pos), 'type': 'SCALAR'}); attrs['_MAT'] = a_mt
        if b.get('nrm') is not None:
            a_n = len(accs); accs.append({'bufferView': add(np.ascontiguousarray(b['nrm'], np.float32), 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC3'}); attrs['NORMAL'] = a_n
        a_ix = len(accs); accs.append({'bufferView': add(ix, 34963), 'componentType': 5125, 'count': len(ix), 'type': 'SCALAR'})
        mats.append({'name': b['name'], 'pbrMetallicRoughness': {'baseColorFactor': [_lin(c) for c in b['color'][:3]] + [b['color'][3]], 'metallicFactor': 0.0, 'roughnessFactor': 0.85},
                     **({'alphaMode': 'BLEND'} if b['color'][3] < 1 else {}), 'doubleSided': True})
        meshes.append({'name': b['name'], 'primitives': [{'attributes': attrs, 'indices': a_ix, 'material': len(mats) - 1, 'mode': b.get('mode', 4)}], 'extras': {'batch': i}})
        nodes.append({'mesh': len(meshes) - 1, 'name': b['name'], 'extras': {'batch': i}})
    js = {'asset': {'version': '2.0', 'generator': 'rvt-ballet'}, 'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes,
          'meshes': meshes, 'materials': mats, 'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': off}]}
    if extras: js['extras'] = extras
    jb = json.dumps(js, separators=(',', ':')).encode(); jb += b' ' * ((-len(jb)) % 4)
    bn = b''.join(bin_parts)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(jb) + 8 + len(bn)))
        f.write(struct.pack('<I4s', len(jb), b'JSON')); f.write(jb)
        f.write(struct.pack('<I4s', len(bn), b'BIN\0')); f.write(bn)
