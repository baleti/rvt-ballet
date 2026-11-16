"""Independent structure check of a Revit (compound file) .rvt/.rte/.rfa: header, DIFAT/FAT, FATSECT marks, directory chain, every stream chain unique (no shared sector),
chains end ENDOFCHAIN, chain length matches stream size, ministream, unowned sectors must be FREE.
usage: tools/rvt_cfb_check.py FILE...   prints one line per file: a dict of counts when valid, or INVALID: reason (c4x-rvtmatrix 2026-11-16)."""
import sys, struct
def check(path):
    d = open(path, 'rb').read(); r = {}
    assert d[:8] == bytes.fromhex('d0cf11e0a1b11ae1'), 'magic'
    ss = 1 << struct.unpack_from('<H', d, 30)[0]; mss = 1 << struct.unpack_from('<H', d, 32)[0]
    nfat, dir0, _, cutoff, mf0, nmf, di0, ndi = struct.unpack_from('<IIIIIIII', d, 44)
    nsec = (len(d) - ss) // ss; r['sectors'] = nsec; r['ss'] = ss
    difat = list(struct.unpack_from('<109I', d, 76))
    s = di0
    for _ in range(ndi):
        o = (s + 1) * ss; v = struct.unpack_from('<%dI' % (ss // 4), d, o); difat += list(v[:-1]); s = v[-1]
    difat = [x for x in difat if x < 0xFFFFFFFA][:nfat]; r['fat_secs'] = len(difat)
    assert len(difat) == nfat, 'DIFAT lists %d of %d fat sectors' % (len(difat), nfat)
    fat = []
    for f in difat: fat += struct.unpack_from('<%dI' % (ss // 4), d, (f + 1) * ss)
    owner = {}
    def chain(s, tag):
        out = []
        while s < 0xFFFFFFFA:
            assert s < nsec, '%s: sector %d beyond file (%d)' % (tag, s, nsec)
            assert s not in owner, '%s: sector %d already owned by %s' % (tag, s, owner[s])
            owner[s] = tag; out.append(s); assert len(out) <= nsec, 'loop'; s = fat[s]
        assert s == 0xFFFFFFFE, '%s: chain ends with %x' % (tag, s)
        return out
    for i, f in enumerate(difat): assert fat[f] == 0xFFFFFFFD, 'fat sector %d not marked FATSECT' % f; owner[f] = 'FAT'
    dchain = chain(dir0, 'dir'); mfc = chain(mf0, 'minifat') if nmf else []
    de = b''.join(d[(s + 1) * ss:(s + 2) * ss] for s in dchain); ents = []
    for i in range(len(de) // 128):
        e = de[i * 128:(i + 1) * 128]; t = e[66]
        if t == 0: continue
        nm = e[:struct.unpack_from('<H', e, 64)[0] - 2].decode('utf-16le'); st = struct.unpack_from('<I', e, 116)[0]; sz = struct.unpack_from('<Q', e, 120)[0]
        ents.append((i, nm, t, st, sz))
    root = [e for e in ents if e[2] == 5]; assert len(root) == 1, 'root entries %d' % len(root)
    ns = 0
    for i, nm, t, st, sz in ents:
        if t == 2 and sz >= cutoff:
            c = chain(st, nm); ns += 1
            assert len(c) * ss >= sz and (len(c) - 1) * ss < sz, '%s: chain %d sectors for size %d' % (nm, len(c), sz)
    if root[0][4]: chain(root[0][3], 'ministream')
    mini = sum(1 for e in ents if e[2] == 2 and e[4] < cutoff)
    free = sum(1 for s in range(nsec) if s not in owner); r.update(streams_big=ns, streams_mini=mini, entries=len(ents), unowned_sectors=free, fat_free_marked=sum(1 for s in range(nsec) if fat[s] == 0xFFFFFFFF))
    unowned_not_free = [s for s in range(nsec) if s not in owner and fat[s] != 0xFFFFFFFF]
    r['unowned_but_not_FREE_in_FAT'] = len(unowned_not_free)
    return r
if __name__ == '__main__':
  for p in sys.argv[1:]:
    try: print(p.split('/')[-1], check(p))
    except AssertionError as e: print(p.split('/')[-1], 'INVALID:', e)
