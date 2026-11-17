"""set-num on a ProfileRoof (Autodesk Snowdon Facades 2024, 1247078) is refused (offset/dimension numbers drive stored geometry that Revit regenerates), no output file; class check also covers ceiling/roof names."""
import os, sys, subprocess, tempfile, shutil
S = os.path.expanduser('~/rvtfix/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
if not os.path.exists(S): print('skip'); sys.exit(0)
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, R)
from rvtballet import edit
for cls in ('ProfileRoof', 'Roof', 'FootPrintRoof', 'CeilingElem', 'Ceiling'): assert edit._setnum_geom_class(cls), cls
for cls in ('RoofAttributes', 'CompoundCeilingType', 'RoofSoffitType'): assert not edit._setnum_geom_class(cls), cls     # type/attribute elements go through set-type-num
d = tempfile.mkdtemp(dir=os.path.expanduser('~/c3x-tmp-c4x'))
try:
    o = d + '/o.rvt'
    p = subprocess.run([R + '/bin/rvt-ballet', 'edit', S, '-o', o, '--set-num', '1247078', 'Base Offset From Level', '1.0'], capture_output=True, text=True, timeout=900)
    print((p.stdout + p.stderr)[:160])
    assert 'floor, wall, ceiling or roof' in p.stdout + p.stderr and not os.path.exists(o)
    print('ok roof set-num refused')
finally: shutil.rmtree(d, ignore_errors=True)
