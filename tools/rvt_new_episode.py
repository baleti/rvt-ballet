#!/usr/bin/env python3
"""rvt_new_episode.py BEFORE.rvt EDITED.rvt OUT.rvt: LAB/EXPERIMENT. Give an edit made by our writer (EDITED, derived from BEFORE) Revit's 'new episode'
bookkeeping, as decoded from 28 Revit-made base->after pairs (RVT-PATTERNS.md): ElemTable triples (new row = EP x3; touched row B,C := EP), History (+17 B),
DocumentIncrementTable (tools/rvt_dit_episode.py), BasicFileInfo (tools/rvt_bfi_episode.py), Contents (tools/rvt_contents_episode.py).
EP = the DIT top record's epB in BEFORE. Writes OUT only. Autodesk samples / synthetic only. Not wired into any product save path; output is UNVERIFIED until a Revit VM open."""
import os, sys, struct, time, uuid
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import adiff, wledit
import rvt_dit_episode as D, rvt_bfi_episode as B, rvt_contents_episode as C
def main(before, edited, out):
    if os.path.realpath(out) in (os.path.realpath(before), os.path.realpath(edited)): sys.exit('REFUSED: output equals an input')
    dit0 = adiff.graw(before, 'Global/DocumentIncrementTable')
    EP = D.top_epb(dit0)
    et0 = adiff.graw(before, 'Global/ElemTable'); n0 = struct.unpack_from('<I', et0, 2)[0]
    old = {struct.unpack_from('<Q', et0, 6 + 40 * k)[0]: et0[6 + 40 * k:6 + 40 * k + 40] for k in range(n0)}
    ed = wledit.Editor(edited)
    st = {}
    def et(raw):
        raw = bytearray(raw); n = struct.unpack_from('<I', raw, 2)[0]; st['rows'] = n; st['new'] = st['chg'] = 0
        for k in range(n):
            o = 6 + 40 * k; i = struct.unpack_from('<Q', raw, o)[0]
            if i not in old: struct.pack_into('<3I', raw, o + 8, EP, EP, EP); st['new'] += 1
            elif str(i) in os.environ.get('EP_TOUCH', '').split(','):      # experiment: rows Revit touched without a content diff in OUR edit (B := EP)
                a, _, c = struct.unpack_from('<3I', raw, o + 8); struct.pack_into('<3I', raw, o + 8, a, EP, c)
            elif bytes(raw[o:o+40]) != old[i]:
                a = struct.unpack_from('<I', raw, o + 8)[0]; struct.pack_into('<3I', raw, o + 8, a, EP, EP); st['chg'] += 1
        return bytes(raw)
    def hist(raw):
        raw = bytearray(raw); raw[14] = (raw[14] + 1) & 255
        pat = b'\x66\x0a\x00\x00' + struct.pack('<I', EP); k = bytes(raw).find(pat)
        assert k >= 0, 'History episode field not found'
        k += 4; raw[k:k+4] = struct.pack('<I', EP + 1) + uuid.uuid4().bytes_le + b'\x28'
        return bytes(raw)
    drows = [0]
    only_rename = bool(os.environ.get('EP_ONLY_RENAME'))      # experiment: partition rename alone
    et_only = bool(os.environ.get('EP_ET_ONLY'))      # experiment: only the ElemTable triples (new row = EP x3), nothing else (no rename: it was harmful, c4x 2026-11-09)
    c = ed.m.c; S = c.streams()
    if et_only:
        ed.global_edit('Global/ElemTable', et); ed.save(out); print('OK (ElemTable only) EP=%d new=%d chg=%d' % (EP, st['new'], st['chg'])); return
    if not only_rename:
        ed.global_edit('Global/ElemTable', et)
        drows[0] = st['rows'] - n0
        ed.global_edit('Global/History', hist)
        ed.global_edit('Global/DocumentIncrementTable', lambda x: D.dit_next(x, int(os.environ.get('EP_TIME') or time.time()), drows[0]))
    parts = [n for n in S if n.startswith('Partitions/')]
    if len(parts) == 1 and not os.environ.get('EP_NO_RENAME'):      # Revit renames the single partition stream to old+1 on every save (42->43, 21->22; = DIT save counter)
        e = S[parts[0]]; new = str(int(parts[0].split('/')[1]) + 1)
        raw = bytearray(e.raw); nb = new.encode('utf-16le') + b'\0\0'
        raw[0:64] = nb + b'\0' * (64 - len(nb)); raw[64:66] = struct.pack('<H', len(nb)); e.raw = bytes(raw); e.name = new
        print('partition stream renamed %s -> Partitions/%s' % (parts[0], new))
    if only_rename: ed.save(out); print('OK (rename only)'); return
    bfi = bytes(S['BasicFileInfo'].data); order = []
    for m in B.GUID.finditer(bfi):
        if m.group(0) not in order and m.group(0) != B.ZERO: order.append(m.group(0))
    S['BasicFileInfo'].data, _ = B.bfi_next(bfi, [str(uuid.uuid4()) for _ in order])
    S['Contents'].data = C.contents_next(bytes(S['Contents'].data), D.top_counters(dit0))
    ed.save(out)
    print('OK EP=%d rows %d->%d new=%d changed=%d' % (EP, n0, st['rows'], st['new'], st['chg']))
if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:4])
