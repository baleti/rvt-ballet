"""TEST TOOL: mutate a change_type / edit output for gate escape hunts: MUT=row_pad (junk in the padding of the instance's ElemTable row) | row_inc (the row's increment field changed) | stray_rec (flip one byte in the record of a DIFFERENT, undeclared element). usage: MUT=row_pad tools/rvt_ct_mut.py IN.rvt OUT.rvt INSTANCE_EID  (Autodesk samples only)"""
import sys, os, struct
sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
os.environ['RVT_GEOM'] = '1'
import rvtgen
src, dst, inst = sys.argv[1], sys.argv[2], int(sys.argv[3]); M = os.environ['MUT']
g = rvtgen.Gen(src)
if M in ('row_pad', 'row_inc'):
    RW = g.RW
    def fn(raw):
        n = struct.unpack_from('<I', raw, 2)[0]; out = bytearray(raw)
        for k in range(n):
            r = 6 + RW * k
            if struct.unpack_from('<Q', out, r)[0] == inst:
                if M == 'row_pad': out[r + 36:r + 40] = b'\xee' * 4
                else: struct.pack_into('<I', out, r + 12, struct.unpack_from('<I', out, r + 12)[0] + 1)
                return bytes(out)
        raise SystemExit('row for %d not found' % inst)
    g.e.global_edit('Global/ElemTable', fn)
else:
    other = int(os.environ.get('OTHER', '0')) or None
    if not other: sys.exit('stray_rec needs OTHER=<undeclared element id> (an element other than the instance)')
    T = g.template(other); rec = bytearray(T['rec']); rec[-9] ^= 1; g.replace_existing(other, rec=bytes(rec))
g.commit(dst); print('ok', dst)
