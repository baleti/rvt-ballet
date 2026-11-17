#!/usr/bin/env python3
"""rvt_join_set_cmp.py A.rte B.rte EID [EID...]: print and compare CurveDriver.m_controlJoinsSet (and presence) of the given FamilyInstance ids in two files
(e.g. our join-cleanup candidate vs the Revit-made delete). Exit 0 if equal for all ids, 1 otherwise. Autodesk samples / synthetic only; read-only."""
import sys, os, json
sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
import rvt_xcache
def find(o, key, res):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: res.append(v)
            else: find(v, key, res)
    elif isinstance(o, list):
        for v in o: find(v, key, res)
def sets(path, eids):
    x = rvt_xcache.get_x_ro(path); out = {}
    for e in eids:
        r = x['recs'].get((e, 'FamilyInstance'))
        if r is None: out[e] = 'ABSENT'; continue
        t = []; find(r.get('fields'), 'm_controlJoinsSet', t); out[e] = t
    return out
if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]; ids = [int(i) for i in sys.argv[3:]]
    sa, sb = sets(a, ids), sets(b, ids); rc = 0
    for e in ids:
        same = json.dumps(sa[e], sort_keys=True, default=str) == json.dumps(sb[e], sort_keys=True, default=str); rc |= (not same)
        print(e, 'EQUAL' if same else 'DIFFER', '\n  A:', json.dumps(sa[e], default=str)[:300], '\n  B:', json.dumps(sb[e], default=str)[:300])
    sys.exit(rc)
