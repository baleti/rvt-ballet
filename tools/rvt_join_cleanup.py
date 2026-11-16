#!/usr/bin/env python3
"""rvt_join_cleanup.py SRC OUT EID  (EXPERIMENTAL, not wired into the product, not VM-verified)
Delete FamilyInstance EID and clear its join partners: every other instance whose CurveDriver.m_controlJoinsSet (IndexJoinPair[] with CDJoinInfo.m_info naming EID) lists EID gets
that set emptied (count 0) when ALL its pairs involve only itself and EID; otherwise the tool refuses (a partner with other joins needs a per-pair edit not derived yet).
Step 1 = the product delete path (RVTBALLET_ENABLE_DELETE=1 needed); step 2 = wledit.modify on each partner. Derived offline from write-lab mcls1 (c4x-rvtdiff 262); the Revit-made delete decides.
Autodesk samples / synthetic only; writes only OUT, never SRC."""
import sys, os, re, struct, json, tempfile, shutil
sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
def main(src, out, eid):
    if os.path.abspath(src) == os.path.abspath(out): raise SystemExit('OUT is the input: refusing')
    os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    import rvt_xcache, wledit
    from rvtballet import edit
    x = rvt_xcache.get_x_ro(src); partners = {}
    def find(o, key, res):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key: res.append(v)
                else: find(v, key, res)
        elif isinstance(o, list):
            for v in o: find(v, key, res)
    for (e, c), r in x['recs'].items():
        if c != 'FamilyInstance' or e == eid: continue
        t = []; find(r.get('fields'), 'm_controlJoinsSet', t)
        for js in t:
            pairs = js if isinstance(js, list) else []
            named = set()
            for p in pairs:
                inf = []; find(p, 'm_elemId', inf)
                named |= {int(re.findall(r'\d+', str(v))[0]) for v in inf}
            if eid in named:
                if named - {eid, e}: raise SystemExit('partner %d has joins with other elements %s: not derived, refused' % (e, sorted(named - {eid, e})))
                partners[e] = len(pairs)
    for e in [eid] + sorted(partners):      # column/wall style joins (m_affectedEdgesTags, e.g. Facades 2024 column 593361) are a different structure: not derived, refused
        r = x['recs'].get((e, 'FamilyInstance')); t = []; find(r.get('fields') if r else None, 'm_affectedEdgesTags', t)
        if any(t): raise SystemExit('element %d also has m_affectedEdgesTags joins (column/wall style): not derived, refused' % e)
    buf = open(src, 'rb').read()
    nb, _ = edit.apply_full(buf, [edit.validate_op({'op': 'delete', 'eid': eid})])
    d = tempfile.mkdtemp(prefix='rvtjoin-')
    try:
        ext = os.path.splitext(out)[1] or '.rte'; cur = os.path.join(d, 's1' + ext); open(cur, 'wb').write(nb)
        for p in sorted(partners):
            e = wledit.Editor(cur); pn, i, r, log, q = e.trace(p)
            ent = [l for l in log if l[1] == 'CurveDriver.m_controlJoinsSet'][0]
            e.modify(p, [(ent[2], ent[3] - ent[2], struct.pack('<I', 0))]); nxt = os.path.join(d, 's%d%s' % (p, ext)); e.save(nxt); cur = nxt
        shutil.copyfile(cur, out)
    finally: shutil.rmtree(d, ignore_errors=True)
    print('wrote', out, 'deleted', eid, 'cleared partners', sorted(partners))
if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
