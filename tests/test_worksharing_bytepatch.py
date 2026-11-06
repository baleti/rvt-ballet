"""worksharing_state() parses a REAL byte-level BasicFileInfo change (not a monkeypatch): Autodesk 2024 template copy with 'Not enabled' rewritten to 'Central'/'Local' (UTF-16, same length)."""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
src = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2024/71_*.rte')))[0]
b = open(src, 'rb').read(); old = 'Not enabled'.encode('utf-16le')
assert save.worksharing_state(b) == 'Not enabled'
n = b.count(old); assert n == 1, n
for v in ('Central', 'Local'):
    nb = b.replace(old, (v + ' ' * (11 - len(v))).encode('utf-16le'))
    assert save.worksharing_state(nb) == v, (v, save.worksharing_state(nb))
print('worksharing byte-patch parse OK (Central, Local)')
