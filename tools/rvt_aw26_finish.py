#!/usr/bin/env python3
"""rvt_aw26_finish.py BEFORE.rvt EDITED.rvt OUT.rvt: LAB/EXPERIMENT (c4x-rvtdiff 2026-11-12). Turns our 2026 add-wall output (EDITED, derived from the Revit-saved BEFORE) into the file
Revit 2026 opened in the VM (y12; y14 = this pipeline is the pure-tools test): (1) partition header stamps old EP -> EP (rvt_ep_stamp.stamp_entries), (2) wall chunk flag 0x1f->0x1e
and Adler32 (find_chunks/fix_chunk), (3) oversize partition member cut like Revit (rvt_split_oversize), (4) new-episode bookkeeping (rvt_new_episode: ElemTable/History/DIT/BFI, rename
partition n -> n+1, Contents untouched). Single-partition (Revit-saved) bases only. Writes OUT only; refuses when a step does not apply. UNVERIFIED until a VM verdict + readback."""
import os, sys, subprocess, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
def main(before, edited, out):
    if os.path.realpath(out) in (os.path.realpath(before), os.path.realpath(edited)): sys.exit('REFUSED: output equals an input')
    import wledit, adiff, numpy as np
    import rvt_dit_episode as D, rvt_ep_stamp as T, rvt_split_oversize as SP
    ep = D.top_epb(adiff.graw(before, 'Global/DocumentIncrementTable'))
    ed = wledit.Editor(edited)
    names = [k for k in ed.m.parts]
    if len(names) != 1: sys.exit('REFUSED: %d partitions; only Revit-saved single-partition bases are handled' % len(names))
    pn = names[0]; pt = ed.part(pn); joined = bytes(ed.m.parts[pn]['joined'])
    st, n = T.stamp_entries(joined, ep - 1, ep)
    if n == 0: sys.exit('REFUSED: no partition header entry holds the previous episode %d; the stamp rule does not apply' % (ep - 1))
    ch = T.find_chunks(st)
    if len(ch) != 1:      # Revit-saved bases can hold chunks with the same marker of their own (Electrical: 2): keep only those that are NEW (not present, by adler+length, in BEFORE)
        bm = wledit.Editor(before).m; bj = bytes(bm.parts[list(bm.parts)[0]]['joined'])
        old = {(struct.unpack_from('<I', bj, c + 8)[0], struct.unpack_from('<I', bj, c + 12)[0]) for c in T.find_chunks(bj)}
        ch = [c for c in ch if (struct.unpack_from('<I', st, c + 8)[0], struct.unpack_from('<I', st, c + 12)[0]) not in old]
    if len(ch) != 1: sys.exit('REFUSED: expected exactly one NEW wall chunk with a stale flag, found %d' % len(ch))
    fx = T.fix_chunk(st, ch[0])
    A = np.frombuffer(joined, np.uint8); B = np.frombuffer(fx, np.uint8); idx = np.nonzero(A != B)[0].tolist(); runs = []
    for i in idx:
        if runs and i - runs[-1][1] <= 1: runs[-1][1] = i
        else: runs.append([i, i])
    for s, e in runs: pt.replace(s, e - s + 1, fx[s:e + 1])
    cuts = SP.split_oversize(pt)
    tmp = out + '.finish.tmp'
    try:
        ed.save(tmp)
        r = subprocess.call([sys.executable, os.path.join(H, 'rvt_new_episode.py'), before, tmp, out])
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    if r != 0:
        if os.path.exists(out): os.remove(out)
        sys.exit('REFUSED: episode composer failed')
    print('OK EP=%d stamps=%d chunk@%d changed_bytes=%d cuts=%s' % (ep, n, ch[0], len(idx), cuts))
if __name__ == '__main__':
    main(*sys.argv[1:4])
