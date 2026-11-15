"""rvt_linkadd_streams.py: offline stream-level pieces of a Revit link add, derived from ONE Revit-made pair (see ~/demo-state/rvt-edit/linkadd-layout.md).
Pure functions on DECOMPRESSED payloads; NOT a complete link add (partition records, Latest lists, increment table are not done), so nothing here may be wired to a save path.
  elemtable_append(payload, rows)  rows = [(id, x, y), ...] ascending ids > current max
  transmission_append(payload, elem_id, path)
Self test: python3 rvt_linkadd_streams.py NOOP.rvt ADDED.rvt  (Autodesk-sample-derived pair) -> reproduces the Revit-made payloads byte for byte."""
import struct, sys, os
def elemtable_append(p, rows):
    n = struct.unpack_from('<I', p, 2)[0]; body_end = 6 + 40 * n; tail = bytearray(p[body_end:])
    if len(tail) != 24: raise ValueError('unexpected ElemTable trailer length %d' % len(tail))
    last = struct.unpack_from('<I', tail, 12)[0]; out = bytearray(p[:body_end])
    for (i, x, y) in rows:
        if i <= last: raise ValueError('new id %d not above current last id %d' % (i, last))
        out += struct.pack('<IIIIIIIIII', i, 0, x, x, y, i, 0, 0xffffffff, 0xffffffff, 0); last = i
    struct.pack_into('<I', out, 2, n + len(rows)); struct.pack_into('<I', tail, 12, last)
    return bytes(out + tail)
def transmission_append(raw, elem_id, path, kind='Revit Link'):
    n = struct.unpack_from('<I', raw)[0]; xml = raw[4:].decode('utf-16le')
    if len(xml) != n or not xml.rstrip().endswith('</TransmissionData>'): raise ValueError('unexpected TransmissionData layout')
    ref = ('<ExternalFileReference><ElementId>%d</ElementId><ExternalFileReferenceType>%s</ExternalFileReferenceType><LastSavedPath>%s</LastSavedPath><LastSavedAbsolutePath>%s</LastSavedAbsolutePath><LastSavedPathType>Absolute</LastSavedPathType><LastSavedLoadState>Loaded</LastSavedLoadState><DesiredPath>%s</DesiredPath><DesiredPathType>Absolute</DesiredPathType><DesiredLoadState>Loaded</DesiredLoadState></ExternalFileReference>' % (elem_id, kind, path, path, path))
    k = xml.rindex('</TransmissionData>'); xml = xml[:k] + ref + xml[k:]
    return struct.pack('<I', len(xml)) + xml.encode('utf-16le')
def _main(a, b):
    for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
    import rvtfmt, olefile
    def g(f, s): return olefile.OleFileIO(f).openstream(s).read()
    ea = rvtfmt.inflate_stream(g(a, 'Global/ElemTable'))[1]; eb = rvtfmt.inflate_stream(g(b, 'Global/ElemTable'))[1]
    got = elemtable_append(ea, [(1542984, 1099, 1099), (1542985, 1099, 1099), (1542986, 1099, 0xffffffff)])
    ok1 = got == eb; print('ElemTable payload reproduced:', ok1, len(got), len(eb))
    ta, tb = g(a, 'TransmissionData'), g(b, 'TransmissionData')
    got = transmission_append(ta, 1542984, 'C:\\wl\\la_tgt.rvt'); ok2 = got == tb; print('TransmissionData reproduced:', ok2, len(got), len(tb))
    sys.exit(0 if ok1 and ok2 else 1)
if __name__ == '__main__': _main(*sys.argv[1:3])

def latest_append_after_tail(p, tail_id, new_id):
    """Latest payload: for every id-list [u32 count][u64 ids ascending] whose LAST entry is tail_id, append new_id and bump the count. Returns (new payload, number of lists changed). Lists are found by the u64 value tail_id followed by a non-ascending word and preceded by an ascending run with a matching u32 count."""
    key = struct.pack('<Q', tail_id); out = bytearray(); pos = 0; hits = 0; i = p.find(key)
    cuts = []
    while i != -1:
        q = i; n = 1; prev = tail_id
        while True:
            v = struct.unpack_from('<Q', p, q - 8)[0]
            if v == 0 or v >= prev or v >= 2 ** 24: break
            prev = v; q -= 8; n += 1
        if struct.unpack_from('<I', p, q - 4)[0] == n: cuts.append((q - 4, i + 8, n))
        i = p.find(key, i + 8)
    for (c, end, n) in cuts:
        out += p[pos:c] + struct.pack('<I', n + 1) + p[c + 4:end] + struct.pack('<Q', new_id); pos = end; hits += 1
    out += p[pos:]; return bytes(out), hits
