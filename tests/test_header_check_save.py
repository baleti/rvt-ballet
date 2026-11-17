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
dd = headercheck.deep_diff(F, out); assert len(dd) == 1 and str(EID) in dd[0], dd      # whole-model layer: finds the rewrite without being told the element
assert headercheck.deep_diff(F, out, {EID}) == [] and headercheck.deep_diff(F, F) == []
# Family body category (FamilyBase.m_categoryId): live in Revit 2024 (VM: a PanelType of the family went Curtain_Panels -> Walls), invisible in headers
FAM = 20915; s2 = segedit.Session(F, part=segedit.partition_of(F, [FAM])); i, r, log, q = s2.trace(FAM)
off = [l[2] for l in log if l[1] == 'FamilyBase.m_categoryId'][0]; s2._replace(off, 8, struct.pack('<q', -2000011), 'famcatflip')
out2 = d + '/famflip.rvt'; s2.write(out2)
fd = headercheck.deep_diff(F, out2); assert len(fd) == 1 and 'Family %d' % FAM in fd[0], fd
assert headercheck.deep_diff(F, out2, {FAM}) == []
hf = headercheck.header_diff(open(F, 'rb').read(), open(out2, 'rb').read(), [FAM]); assert hf and 'body category' in hf[0], hf      # per-edit layer
assert headercheck.header_diff(open(F, 'rb').read(), open(F, 'rb').read(), [FAM]) == []
# production layer: the rewrite is in an element the op does NOT name (op names the Family 20915): only the whole-model layer sees it
os.environ['RVTBALLET_DEEP_CHECK'] = '1'
try: save._readback(src, bad, [{'op': 'set_link_path', 'eid': FAM, 'value': 'x'}]); raise SystemExit('ESCAPE: category flip of an unnamed element accepted')
except Exception as e: assert 'resolved' in str(e), e
os.environ['RVTBALLET_DEEP_CHECK'] = '0'
save._readback(src, bad, [{'op': 'set_link_path', 'eid': FAM, 'value': 'x'}])      # layer off: not seen (documents the switch)
print('ok')
