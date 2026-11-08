"""rvt_diff_vm.cs_for emits the C# for addlevel/addgrid/addcol/type and rejects unknown ops (offline, no VM)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import rvt_diff_vm as m
cs = m.cs_for('addlevel:60;addgrid:0:0:40:0;addcol:12:12;type:5:6', 't', 'C:\\x.rvt')
for needle in ('Level.Create(d, 60)', 'Grid.Create(d', 'NewFamilyInstance(new XYZ(12, 12', 'ChangeTypeId(new ElementId(6L))'):
    assert needle in cs, needle
try: m.cs_for('bogus:1', 't', 'x.rvt'); raise AssertionError('accepted unknown op')
except SystemExit: pass
print('diff_vm new ops OK')
