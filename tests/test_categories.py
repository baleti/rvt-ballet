"""categories.resolve: header builtin kept, positive (sub)category -> parent builtin, body categories for GStyle/surrogates/Family, rest is NOCAT (synthetic)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from rvtballet import categories as C

def run():
    N = C.NOCAT
    ids = np.array([1, 2, 3, 4, 5, 6, 7], dtype=np.uint64)
    cn = np.array(['Wall', 'GStyleElem', 'CategoryElem', 'FamilySurrogate', 'Family', 'FontElem', 'Wall'])
    cls = np.arange(7, dtype=np.uint16)
    cat = np.array([-2000011, -1, -1, -1, -1, -1, 900], dtype=np.int64)       # 7: positive id with no CategoryElem -> unresolved
    M = (1 << 64)
    full = {(2, 'GStyleElem'): {'id': 2, 'fields': {'m_categoryId': 3}},
            (3, 'CategoryElem'): {'id': 3, 'fields': {'m_parentCategoryId': M - 2000059}},
            (4, 'FamilySurrogate'): {'id': 4, 'fields': {'m_categoryId': M - 2001140, 'm_elemId': 5}}}
    out = C.resolve(cat, cls, cn, ids, full, 8).tolist()
    assert out == [-2000011, -2000059, -2000059, -2001140, -2001140, N, N], out
    print('ok')

if __name__ == '__main__': run()
def test_resolve(): run()
