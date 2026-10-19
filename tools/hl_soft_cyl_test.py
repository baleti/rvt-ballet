"""self test of tools/hl_soft.py: a synthetic 24-gon cylinder seen from above must show both silhouette lines (regression: the edge-on silhouette was occluded by its own faces). usage: python tools/hl_soft_cyl_test.py"""
import numpy as np, json, struct, os, subprocess, sys, tempfile
from PIL import Image
d = tempfile.mkdtemp(); N = 24; r = .3; h = 10.0; P = []
for i in range(N):
    a = 2 * np.pi * i / N; P += [[r * np.cos(a), 0, r * np.sin(a)], [r * np.cos(a), h, r * np.sin(a)]]
P += [[0, 0, 0], [0, h, 0]]; P = np.array(P, np.float32); T = []
for i in range(N):
    j = (i + 1) % N; a, b, c, e = 2 * i, 2 * i + 1, 2 * j, 2 * j + 1; T += [[a, c, b], [c, e, b], [2 * N, c, a], [2 * N + 1, b, e]]
T = np.array(T, np.uint32); EI = np.zeros(len(P), np.float32); bin_ = P.tobytes() + EI.tobytes() + T.tobytes()
J = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(bin_)}], 'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': P.nbytes}, {'buffer': 0, 'byteOffset': P.nbytes, 'byteLength': EI.nbytes}, {'buffer': 0, 'byteOffset': P.nbytes + EI.nbytes, 'byteLength': T.nbytes}],
     'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': len(P), 'type': 'VEC3'}, {'bufferView': 1, 'componentType': 5126, 'count': len(P), 'type': 'SCALAR'}, {'bufferView': 2, 'componentType': 5125, 'count': T.size, 'type': 'SCALAR'}],
     'meshes': [{'primitives': [{'attributes': {'POSITION': 0, '_EIDX': 1}, 'indices': 2, 'mode': 4}]}]}
j = json.dumps(J).encode(); j += b' ' * ((4 - len(j) % 4) % 4); bb = bin_ + b'\0' * ((4 - len(bin_) % 4) % 4)
open(d + '/model.glb', 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(j) + 8 + len(bb)) + struct.pack('<I', len(j)) + b'JSON' + j + struct.pack('<I', len(bb)) + b'BIN\0' + bb)
json.dump({'elements': [[1, 'X', 'Structural Foundations', None, 'pile', None, 'mesh']], 'bbox': [[-1, -1, -1], [1, 1, 12]], 'defaultHidden': []}, open(d + '/meta.json', 'w'))
open(d + '/cameras.tsv', 'w').write('1\tv\t0 0 0\t0.37 -0.48 -0.8\t0 0 1\tFalse\tstyle=HLR\n')
out = d + '/o.png'; p = subprocess.run([sys.executable, os.path.dirname(os.path.abspath(__file__)) + '/hl_soft.py', d, d + '/cameras.tsv', '1', out, '--size', '500'], capture_output=True, text=True)
if p.returncode: print(p.stderr[-400:]); sys.exit(1)
im = np.asarray(Image.open(out)) < 128; cols = im.sum(0); tall = int((cols > 0.6 * im.shape[0] * 0.6).sum())
print('columns with a long vertical line:', tall, '(expect >= 2)'); ok = tall >= 2; print('HL-SOFT-CYL-TEST OK' if ok else 'HL-SOFT-CYL-TEST FAIL'); sys.exit(0 if ok else 1)
