#!/usr/bin/env python3
"""ole_consistency.py FILE... : independent structural check of an OLE/CFB container (the .rvt / .rte wrapper), written from the MS-CFB layout, no olefile.
Findings (each is a problem): header magic/sizes, sector count vs file size, DIFAT chain + unused DIFAT entries not FREESECT, FAT entries that name sectors beyond the file,
FAT sectors not marked FATSECT, DIFAT sectors not marked DIFSECT, a chain that loops, ends in a non-ENDOFCHAIN, or shares a sector with another chain (cross link),
sectors marked used but reachable from nothing (leak), directory tree (entry types, child/sibling indexes in range and acyclic, stream start sector valid, size vs chain length),
mini FAT / mini stream consistency.  Exit 0 = no findings.  Library use: check(path_or_bytes) -> list of strings.  Tests: tests/test_ole_consistency.py (synthetic only)."""
import struct, sys
FREE, END, FATSEC, DIFSEC = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC
MAGIC = bytes.fromhex('D0CF11E0A1B11AE1')

def check(src):
    d = src if isinstance(src, (bytes, bytearray)) else open(src, 'rb').read()
    P = []
    if len(d) < 512 or d[:8] != MAGIC: return ['bad magic or shorter than a header']
    bom, ssh, msh = struct.unpack_from('<HHH', d, 0x1C)
    if bom != 0xFFFE: P.append('byte order mark %04x' % bom)
    if ssh not in (9, 12): return P + ['sector shift %d' % ssh]
    if msh != 6: P.append('mini sector shift %d' % msh)
    ss = 1 << ssh; ms = 1 << msh
    nfat, dirstart, _, cutoff, minifat0, nminifat, difat0, ndifat = struct.unpack_from('<IIIIIIII', d, 0x2C)
    # header fields a conforming reader ignores (and so a dead-byte flip could pass unnoticed); Revit rejected a flip in the unused DIFAT part, so treat deviations as findings (0 on the local corpus)
    major, minor = struct.unpack_from('<HH', d, 0x1A)[0], struct.unpack_from('<H', d, 0x18)[0]
    if (major, ssh) not in ((3, 9), (4, 12)): P.append('major version %d with sector shift %d' % (major, ssh))
    if minor != 0x3E: P.append('minor version %04x' % minor)
    if any(d[0x08:0x18]): P.append('header CLSID not zero')
    if any(d[0x22:0x28]): P.append('header reserved bytes not zero')
    if ssh == 9 and struct.unpack_from('<I', d, 0x28)[0]: P.append('directory sector count set in a v3 file')
    if struct.unpack_from('<I', d, 0x34)[0] != 0: P.append('transaction signature %08x' % struct.unpack_from('<I', d, 0x34)[0])
    if cutoff != 4096: P.append('mini stream cutoff %d' % cutoff)
    hdr = ss if ss > 512 else 512; nsec = (len(d) - hdr) // ss
    if (len(d) - hdr) % ss: P.append('file size %d is not header + n*%d (partial last sector of %d bytes)' % (len(d), ss, (len(d) - hdr) % ss))
    off = lambda s: (s + 1) * ss
    def sec(s): return d[off(s):off(s) + ss]
    if not ndifat and difat0 != END: P.append('first DIFAT sector %08x although the DIFAT is empty' % difat0)
    # DIFAT
    fatsecs = [x for x in struct.unpack_from('<109I', d, 0x4C)]
    difsecs = []; s = difat0; seen = set()
    while s not in (END, FREE) and ndifat:
        if s >= nsec or s in seen: P.append('DIFAT chain broken/looped at %d' % s); break
        seen.add(s); difsecs.append(s); w = struct.unpack('<%dI' % (ss // 4), sec(s)); fatsecs += list(w[:-1]); s = w[-1]
        if len(difsecs) > ndifat + 1: P.append('DIFAT chain longer than header count'); break
    if len(difsecs) != ndifat: P.append('DIFAT sector count %d, header says %d' % (len(difsecs), ndifat))
    used = [x for x in fatsecs if x != FREE]
    if len(used) != nfat: P.append('header FAT sector count %d, DIFAT lists %d' % (nfat, len(used)))
    # unused entries must be FREESECT everywhere: used entries form a prefix
    first_free = next((i for i, x in enumerate(fatsecs) if x == FREE), len(fatsecs))
    if any(x != FREE for x in fatsecs[first_free:]): P.append('unused DIFAT entries are not all FREESECT (used entries not a prefix)')
    for x in used:
        if x >= nsec: P.append('FAT sector %d beyond file (%d sectors)' % (x, nsec)); return P
    fat = []
    for x in used: fat += list(struct.unpack('<%dI' % (ss // 4), sec(x)))
    if len(set(used)) != len(used): P.append('a FAT sector is listed twice in the DIFAT')
    for x in used:
        if x < len(fat) and fat[x] != FATSEC: P.append('FAT sector %d is not marked FATSECT in the FAT (%08x)' % (x, fat[x]))
    for x in difsecs:
        if x < len(fat) and fat[x] != DIFSEC: P.append('DIFAT sector %d is not marked DIFSECT (%08x)' % (x, fat[x]))
    if len(fat) < nsec: P.append('FAT covers %d sectors, file has %d' % (len(fat), nsec))
    for i, v in enumerate(fat[:nsec]):
        if v not in (FREE, END, FATSEC, DIFSEC) and v >= nsec: P.append('FAT[%d] = %d beyond file' % (i, v))
    owner = {}
    def chain(start, what, tab=None, limit=None):
        tab = fat if tab is None else tab; out = []; s = start; seenl = set()
        while s != END:
            if s >= len(tab) or (tab is fat and s >= nsec): P.append('%s: sector %d out of range' % (what, s)); return out
            if s in seenl: P.append('%s: chain loops at %d' % (what, s)); return out
            if tab[s] in (FREE, FATSEC, DIFSEC): P.append('%s: chain enters sector %d marked %08x' % (what, s, tab[s])); return out
            seenl.add(s); out.append(s)
            if tab is fat:
                if s in owner: P.append('%s: sector %d also belongs to %s (cross link)' % (what, s, owner[s]))
                owner[s] = what
            s = tab[s]
        return out
    # directory
    dsecs = chain(dirstart, 'directory')
    nds = struct.unpack_from('<I', d, 0x28)[0]
    if ssh == 12 and dsecs and nds != len(dsecs): P.append('header says %d directory sectors, chain has %d' % (nds, len(dsecs)))
    dd = b''.join(sec(x) for x in dsecs); ents = []
    for i in range(len(dd) // 128):
        e = dd[i * 128:(i + 1) * 128]; nl = struct.unpack_from('<H', e, 64)[0]; typ = e[66]
        l, r, c = struct.unpack_from('<III', e, 68); st = struct.unpack_from('<I', e, 116)[0]; sz = struct.unpack_from('<Q', e, 120)[0]
        ents.append((typ, nl, l, r, c, st, sz, e[:max(nl - 2, 0)].decode('utf-16le', 'replace')))
    if not ents or ents[0][0] != 5: return P + ['directory entry 0 is not the root storage']
    n = len(ents)
    for i, (typ, nl, l, r, c, st, sz, nm) in enumerate(ents):
        if typ not in (0, 1, 2, 5): P.append('dir %d: bad object type %d' % (i, typ)); continue
        if typ == 0: continue
        if nl == 0 or nl > 64 or nl % 2: P.append('dir %d: bad name length %d' % (i, nl))
        for k, v in (('left', l), ('right', r), ('child', c)):
            if v != FREE and v >= n: P.append('dir %d: %s index %d out of range' % (i, k, v))
    # tree walk from root: acyclic, each entry once
    visited = set()
    def walk(i, depth=0):
        if i == FREE or i >= n: return
        if i in visited: P.append('dir tree visits entry %d twice (cycle or shared node)' % i); return
        if depth > 4000: P.append('dir tree too deep'); return
        visited.add(i); walk(ents[i][2], depth + 1); walk(ents[i][3], depth + 1); walk(ents[i][4], depth + 1)
    walk(0)
    for i, e in enumerate(ents):
        if e[0] != 0 and i not in visited: P.append('dir %d (type %d) not reachable from the root' % (i, e[0]))
    # mini fat + mini stream
    minifat = []
    if nminifat or minifat0 != END:
        msecs = chain(minifat0, 'minifat')
        if len(msecs) != nminifat: P.append('mini FAT has %d sectors, header says %d' % (len(msecs), nminifat))
        for x in msecs: minifat += list(struct.unpack('<%dI' % (ss // 4), sec(x)))
    root = ents[0]; ministream = b''
    if root[5] != END:
        rs = chain(root[5], 'ministream'); ministream = b''.join(sec(x) for x in rs)
        if root[6] > len(rs) * ss: P.append('root stream size %d exceeds its %d sectors' % (root[6], len(rs)))
    # streams
    for i, (typ, nl, l, r, c, st, sz, nm) in enumerate(ents):
        if typ != 2: continue
        if sz < cutoff:
            if sz == 0: continue
            ch = chain(st, 'ministream-stream %d' % i, minifat) if minifat else (P.append('dir %d: small stream but no mini FAT' % i) or [])
            if len(ch) * ms < sz or (len(ch) - 1) * ms >= sz and ch: P.append('dir %d: mini chain %d sectors does not match size %d' % (i, len(ch), sz))
            if ch and max(ch) * ms + ms > len(ministream): P.append('dir %d: mini sector beyond the mini stream' % i)
        else:
            ch = chain(st, 'stream %d' % i)
            if len(ch) * ss < sz or (len(ch) - 1) * ss >= sz: P.append('dir %d: chain %d sectors does not match size %d' % (i, len(ch), sz))
    # leaks: sectors marked used (not FREE) that nothing owns
    for x in used: owner.setdefault(x, 'FAT')
    for x in difsecs: owner.setdefault(x, 'DIFAT')
    leaks = [i for i in range(min(nsec, len(fat))) if fat[i] != FREE and i not in owner]
    if leaks: P.append('%d sectors marked used but reachable from nothing (first %d)' % (len(leaks), leaks[0]))
    return P

if __name__ == '__main__':
    rc = 0
    for f in sys.argv[1:]:
        p = check(f); rc |= bool(p)
        print('%s: %s' % (f.rsplit('/', 1)[-1], 'OK' if not p else '%d findings: %s' % (len(p), '; '.join(p[:6]))))
    sys.exit(rc)
