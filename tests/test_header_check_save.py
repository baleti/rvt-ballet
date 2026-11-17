"""header check in save._readback: a same-length category rewrite (ECC/CRC valid, made with segedit on the Autodesk 2024 HVAC sample) in the header of an edited element is refused; an identical output passes the header layer. c9x-rvtcat"""
import os, sys, struct, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
F = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt'); EID = 1365188
if not os.path.exists(F): print('skip'); sys.exit(0)
from rvtballet import segedit, save, headercheck
s = segedit.Session(F, part=segedit.partition_of(F, [EID])); T = s.template(EID)
a = [l for l in T['hlog'] if l[0] == 'Identifier.m_id64' and l[3] == str(2**64 - 2001140)][0][1]
s._replace(T['_hk'] + a, 8, struct.pack('<q', -2000011), 'catflip')
d = tempfile.mkdtemp(); out = d + '/flip.rvt'; s.write(out)
src, bad = open(F, 'rb').read(), open(out, 'rb').read()
assert headercheck.header_diff(src, src, [EID]) == []
m = headercheck.header_diff(src, bad, [EID]); assert m and 'changed' in m[0], m
os.environ['RVTBALLET_HEADER_CHECK'] = '1'
try: save._readback(src, bad, [{'op': 'set_link_path', 'eid': EID, 'value': 'x'}]); raise SystemExit('ESCAPE: category flip accepted')
except Exception as e: assert 'header' in str(e), e
print('ok')
