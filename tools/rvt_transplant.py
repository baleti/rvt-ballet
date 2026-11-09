#!/usr/bin/env python3
"""rvt_transplant.py OURS.rvt REVIT_AFTER.rvt OUT.rvt ID [ID...]: LAB/EXPERIMENT. Replace the records of the given element ids in OURS by the records Revit itself wrote in
REVIT_AFTER (same base file, same id space). Used to test whether Revit's own side effects of an edit (e.g. LevelRoomPlan / AllPlanTopologies updated for a new wall)
are what Revit 2026 needs. Keeps OURS' record-chain link (A) and re-links the next record. Writes OUT only. Autodesk samples / synthetic only; never a product path."""
import os, sys, struct
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import wledit
def main(ours, rev, out, ids):
    if os.path.realpath(out) in (os.path.realpath(ours), os.path.realpath(rev)): sys.exit('REFUSED: output equals an input')
    ed = wledit.Editor(ours); er = wledit.Editor(rev); W = ed.m.IDW; hs = 12 + W
    for eid in ids:
        pn_r, i_r, r_r, log_r, q_r = er.trace(eid); rec = bytearray(er.m.parts[pn_r]['joined'][i_r:q_r])
        pn, i, r, log, q = ed.trace(eid); pt = ed.part(pn); b = ed.m.parts[pn]['joined']
        rec[0:4] = b[i:i+4]                                  # our predecessor link
        pt.replace(q, 4, struct.pack('<I', len(rec) - hs))   # next record's A = this record's length
        pt.replace(i, q - i, bytes(rec))
        print('transplanted', eid, 'old', q - i, 'new', len(rec))
    ed.save(out)
if __name__ == '__main__':
    if len(sys.argv) < 5: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], [int(a) for a in sys.argv[4:]])
