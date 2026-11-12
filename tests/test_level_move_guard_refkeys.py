"""regression (ESCAPE): the Level-move guard only followed m_assocLevelId/m_levelId/m_upperLevelId, so 4 of 9 levels of the Autodesk 2022 rst basic sample (694, 196629, 417275, 1351691) were NOT flagged although 1 to 141 elements refer to them via m_refLevelId, SketchPlane.m_datumPlaneId, StairsElement.m_topLevelId, DBViewPlan.m_genElemId. A Level move there would have moved the Level record and left those dependents behind. Now every such level is risky. Autodesk sample, skipped when absent. NOT Revit-verified (the guard only refuses)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/rvt-research/corpus/2022/30_rst_basic_sample_project.rvt')
from rvtballet import save
if not os.path.exists(F): print('skip'); sys.exit(0)
L = [694, 196629, 417275, 1351691]
m = save.membership(open(F, 'rb').read(), L)
r = save.risky_membership(m, [{'op': 'move', 'eid': e} for e in L])
bad = [e for e in L if e not in r]
if bad: print('FAIL levels with dependents not flagged:', bad); sys.exit(1)
print('OK all', len(L), 'levels flagged:', {e: m[e] for e in L})
