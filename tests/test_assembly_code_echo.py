"""Assembly Code edit: the derived Assembly Description is accepted by the read-back only when it is exactly the Uniformat table entry of the NEW code (VM: Revit 2024 derives it live: B2010158 'Ext. Wall - Brick Veneer w/ Stud' -> C3030210 'Suspended Ceilings - Acoustical'), or absent for a code that is not in the table; a wrong description or another parameter is not an echo."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt_params
from rvtballet import save
tab = getattr(rvt_params, '_ASSEMBLY_DESC', {})
if not tab: print('skip (no Uniformat table)'); sys.exit(0)
K = 'Assembly Description|String'; code, desc = next(iter(tab.items()))
x = {'Assembly Code': 'OLD', K: 'old desc'}
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': code, K: desc}) == {K}, 'exact table description must be an echo'
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': code, K: desc + 'x'}) == set(), 'a wrong description is not an echo'
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': code}) == set(), 'a known code that LOST its description is not an echo'
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': 'ZZZ-not-in-table'}) == {K}, 'unknown code: description may disappear'
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': 'ZZZ-not-in-table', K: 'something'}) == set(), 'unknown code must not gain a description'
assert save._assembly_echo('Mark', x, {'Assembly Code': code, K: desc}) == set(), 'only the Assembly Code edit has this echo'
assert save._assembly_echo('Assembly Code', x, {'Assembly Code': 5}) == set()
print('assembly code echo rules ok')
