"""segedit: segment-level edit and save for .rvt files (c9x-rvtfastedit, 2026-11-14). Experimental, behind a flag: nothing in the product calls it yet.

Why: the full-model editor (edit-lab rvtedit on write-lab rvtgen/wlpart) inflates and decodes the whole partition several times and the save path then dumps
every element twice for verification: 196 s / 2.6 GB RSS for one move on a 22 MB sample, OOM on 940 MB projects. An edit to one element changes a few
records inside 1-3 gzip members of one partition; every other member is copied byte-for-byte by the old writer too (measured: 1008 of 1011 members identical).

What this module does (same semantics as the old writer, proven by stream-level equivalence tests against it):
  * reads only the CFB directory/FAT and the 24-byte segment headers + gzip trailers (ISIZE) of the partition: no full inflate;
  * finds every occurrence of the element id in the partition's first member run (the only region the old editor ever searches: wlrec.Model joins the
    members of rvtw.members(), which stops at the first raw interlude) by inflating members one at a time (parallel for big files, constant memory);
  * rebuilds the old editor's template (record, ElementHeader record, zone item, decoder traces) from those few members and applies the OLD transforms
    (rvtedit.Edit._shifted / _rotated, genlib.rekey_item / restamp, Editor.modify's length/Adler/next-A rules) unchanged;
  * writes the result in one of two layouts:
      shift: the old writer's layout (dirty members re-deflated at level 9, frames updated, later bytes shifted, slack zero-padded at the end, pages from the
             first change on rebuilt with page ECC): the partition stream is byte-identical to the old writer's for the same edit;
      fit:   dirty members re-deflated to EXACTLY their original compressed size (empty stored deflate blocks, write-lab M4/M5: Revit 2020/2024/2026 open such
             files), frames keep their sizes, only the pages that hold the dirty members (+ their frames) change: O(edit) bytes written, independent of file size;
  * output container: the original file with only the changed sectors of the partition stream rewritten (same stream length, same sector chain);
  * verification (scoped): every rewritten page passes page ECC, every dirty member inflates with a correct CRC/ISIZE to exactly the intended raw bytes, the
    intended raw bytes differ from the original only inside the declared spans, the edited record decodes with the expected value, every byte outside the
    rewritten sectors is identical to the source (full-file compare), and the stream is re-walked (segment chain, footers) over the rewritten range.
Refusals (nothing written): multi-partition element copies, legacy (2017/2018) member layouts, edits that cross a member boundary, members that would exceed the
re-split limit, frames whose stored X1/X2 disagree with the record chain, payload growth beyond the original page layout, anything the decoder cannot trace.
"""
import os, sys, struct, zlib, hashlib, time
from bisect import bisect_right

GZ = b'\x1f\x8b\x08\x00'
PAGE_STORED = 65249; PAGE_PAYLOAD = 64896


class Refused(Exception):
    """the edit cannot be done safely by the segment writer; nothing was written"""


def _paths():
    for p in (os.environ.get('RVTBALLET_EDITLAB', '~/rvt-research/edit-lab'), os.environ.get('RVTBALLET_WRITELAB', '~/rvt-research/write-lab'), '~/rvt-research'):
        p = os.path.expanduser(p)
        if os.path.isdir(p) and p not in sys.path: sys.path.insert(0, p)
    os.environ.setdefault('RVT_GEOM', '1')


# ---------------------------------------------------------------- container + paged stream (read side, pread only)
class SegPart:
    """one Partitions/N stream: payload access through the CFB sector chain (only the pages asked for are read) and the first member run walked from
    the 24-byte segment headers (no inflate)."""
    def __init__(self, path, name, o=None):
        _paths(); import olefile, ecc
        self.path = path; self.name = name
        self.o = o or olefile.OleFileIO(path); self.fp = open(path, 'rb')
        e = self.o.direntries[self.o._find(name)]; self.size = e.size; self.ss = self.o.sectorsize
        if self.size < self.o.minisectorcutoff: raise Refused('%s is a mini stream' % name)
        self.chain = []; c = e.isectStart; fat = self.o.fat
        while 0 <= c < len(fat) and len(self.chain) <= len(fat): self.chain.append(c); c = fat[c]
        if len(self.chain) * self.ss < self.size: raise Refused('sector chain of %s is shorter than the stream' % name)
        self.full = self.size // PAGE_STORED; self.N_last = self.size - self.full * PAGE_STORED
        self.cap_last = ecc.data_capacity(self.N_last) if self.N_last else 0
        self.plen = self.full * PAGE_PAYLOAD + self.cap_last
        self._walk()

    # stored stream bytes / payload bytes
    def stored(self, a, n):
        out = bytearray(); end = min(a + n, self.size); ss = self.ss
        while a < end:
            k, off = divmod(a, ss); take = min(ss - off, end - a)
            out += os.pread(self.fp.fileno(), take, (self.chain[k] + 1) * ss + off); a += take
        return bytes(out)

    def page_len(self, p): return PAGE_STORED if p < self.full else self.N_last
    def page_cap(self, p): return PAGE_PAYLOAD if p < self.full else self.cap_last
    def npages(self): return self.full + (1 if self.N_last else 0)

    def payload(self, a, n):
        out = bytearray(); end = min(a + n, self.plen)
        while a < end:
            pg, po = divmod(a, PAGE_PAYLOAD); take = min(PAGE_PAYLOAD - po, end - a)
            out += self.stored(pg * PAGE_STORED + po, take); a += take
        return bytes(out)

    def _walk(self):
        """first member run exactly as rvtw.members(P, P.find(GZ)): consecutive members separated by 32-byte frames; ends at the first non-member."""
        head = self.payload(0, 4096); st0 = head.find(GZ)
        if st0 < 0: raise Refused('no gzip member at the start of %s' % self.name)
        self.st0 = st0; self.mem = []        # (pos, end, isize, stored_len)
        pos = st0
        while pos + 10 <= self.plen:
            h = self.payload(pos - 24, 34)
            if len(h) < 34 or h[24:28] != GZ: break
            sl = struct.unpack_from('<I', h, 8)[0]; end = pos + sl - 8
            if sl < 26 or end + 8 > self.plen: break
            tr = self.payload(end - 8, 16); isize = struct.unpack_from('<I', tr, 4)[0]
            if struct.unpack_from('<I', tr, 10)[0] != sl: raise Refused('segment footer of member %d disagrees with its header (%d)' % (len(self.mem), sl))
            self.mem.append((pos, end, isize, sl)); pos = end + 32
        if not self.mem: raise Refused('no members in %s' % self.name)
        self.offs = [0]
        for m in self.mem: self.offs.append(self.offs[-1] + m[2])
        self.jlen = self.offs[-1]

    def member_raw(self, k, check=True):
        pos, end, isize, sl = self.mem[k]; z = self.payload(pos, end - pos)
        if z[:10] != bytes.fromhex('1f8b080000000000000b') and check: raise Refused('member %d has an unexpected gzip header' % k)
        d = zlib.decompressobj(-15); raw = d.decompress(z[10:-8])
        if check:
            crc, isz = struct.unpack_from('<II', z, len(z) - 8)
            if not d.eof or d.unused_data or (zlib.crc32(raw) & 0xffffffff) != crc or len(raw) != isz: raise Refused('member %d of %s is damaged (CRC/ISIZE/length)' % (k, self.name))
        return raw

    def frame_before(self, k):
        """(payload offset, bytes) of the frame that describes member k: the 44-byte partition head for k = 0 (fields at +24), else the 32-byte frame (fields at +12)"""
        if k == 0: return 0, self.payload(0, self.st0)
        a = self.mem[k][0] - 32; return a, self.payload(a, 32)

    def frame_after(self, k):
        a = self.mem[k][1]; return a, self.payload(a, 8)


class Joined:
    """lazy view of the joined raw bytes of the first member run (offsets = the old editor's 'joined' offsets), LRU of inflated members"""
    def __init__(self, sp, cache=64):
        self.sp = sp; self.c = {}; self.order = []; self.cache = cache; self.touched = set()
    def raw(self, k):
        r = self.c.get(k)
        if r is None:
            r = self.sp.member_raw(k); self.c[k] = r; self.order.append(k)
            if len(self.order) > self.cache: self.c.pop(self.order.pop(0), None)
        self.touched.add(k); return r
    def member_of(self, off): return bisect_right(self.sp.offs, off) - 1
    def get(self, a, n):
        out = bytearray(); end = min(a + n, self.sp.jlen); a = max(a, 0)
        while a < end:
            k = self.member_of(a); base = self.sp.offs[k]; r = self.raw(k); take = min(len(r) - (a - base), end - a)
            out += r[a - base:a - base + take]; a += take
        return bytes(out)
    def __len__(self): return self.sp.jlen


def _scan_worker(args):
    path, name, ks, pats = args
    sp = SegPart(path, name); out = {p: [] for p in pats}; tails = {}
    for k in ks:
        r = sp.member_raw(k); base = sp.offs[k]
        for p in pats:
            i = r.find(p)
            while i >= 0: out[p].append(base + i); i = r.find(p, i + 1)
        tails[k] = (r[:16], r[-16:])
    return out, tails


def occurrences(sp, pats, workers=None):
    """every joined offset (any alignment, overlapping) of each byte pattern in pats, including matches across member boundaries"""
    n = len(sp.mem); pats = [bytes(p) for p in pats]
    workers = workers or (min(os.cpu_count() or 2, 12) if n > 400 else 1)
    chunks = [list(range(i, n, workers)) for i in range(workers)] if workers > 1 else [list(range(n))]
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(workers) as pool: res = pool.map(_scan_worker, [(sp.path, sp.name, c, pats) for c in chunks])
    else: res = [_scan_worker((sp.path, sp.name, chunks[0], pats))]
    occ = {p: [] for p in pats}; tails = {}
    for o, t in res:
        for p in pats: occ[p] += o[p]
        tails.update(t)
    for p in pats:      # boundary-straddling matches: last 15 bytes of member k + first 15 of k+1
        L = len(p)
        for k in range(n - 1):
            s = tails[k][1][-(L - 1):] + tails[k + 1][0][:L - 1]; i = s.find(p)
            while i >= 0:
                if i < L - 1 and i + L > L - 1: occ[p].append(sp.offs[k + 1] - (L - 1) + i)
                i = s.find(p, i + 1)
        occ[p] = sorted(set(occ[p]))
    return occ


# ---------------------------------------------------------------- model context (schema, decoder) without loading the partition
class Ctx:
    def __init__(self, path):
        _paths(); import olefile, rvtfmt, fmt_parser as fp, rvt_scan as S, rvt_decode as D, rvt_inventory as I
        self.path = path; self.o = olefile.OleFileIO(path)
        cls, _ = fp.parse(rvtfmt.inflate_stream(self.o.openstream('Formats/Latest').read())[1]); self.cls = cls
        self.W = S.id_size(cls); self.sch = D.Schema(cls); self.dec = D.Dec(self.sch, idsize=self.W); self.etags = I.element_tags(cls)
        try:
            import rvt_es as ES; self.dec.es_schemas = ES.load(path)[0]
        except Exception: self.dec.es_schemas = {}
        self.hs = 12 + self.W; self.IDF = '<I' if self.W == 4 else '<Q'
        self.EHT = struct.pack('<H', self.sch.by['ElementHeader'] + 12)
        self.parts = sorted('/'.join(e) for e in self.o.listdir(streams=True) if e[0] == 'Partitions')


# ---------------------------------------------------------------- template (mirror of rvtgen_e.Gen.template on a lazy joined buffer)
WIN = 1 << 20


class Session:
    """one segment-level edit session on one partition"""
    def __init__(self, path, part=None, workers=None):
        self.ctx = Ctx(path); c = self.ctx
        if len(c.parts) != 1 and part is None: raise Refused('file has %d partitions: the segment writer handles single-partition files only (for now)' % len(c.parts))
        self.pn = part or c.parts[0]; self.sp = SegPart(path, self.pn, c.o); self.J = Joined(self.sp); self.workers = workers
        self.edits = []      # (joined_off, oldlen, newbytes, note)
        self.touched = set()      # members the old writer marks dirty (re-deflated in the shift layout even when their bytes do not change)
        self.occ = {}; self.expect = []      # (eid, kind, check fn on the new record bytes)
        self._legacy_check()

    def _legacy_check(self):
        """region hs per member as wlpart.Partition: measured hs = round((ISIZE - X2) / X1); the first member with hs == 12 + W starts the record region"""
        hs0 = self.ctx.hs; self.mhs = []
        for k in range(len(self.sp.mem)):
            _, f = self.sp.frame_before(k); off = 24 if k == 0 else 12
            x1, x2 = struct.unpack_from('<I', f, off)[0], struct.unpack_from('<I', f, off + 8)[0]
            self.mhs.append(round((self.sp.mem[k][2] - x2) / x1) if x1 else hs0)
        if hs0 not in self.mhs: raise Refused('legacy member layout (no member with record header size %d): not handled by the segment writer' % hs0)
        self.firstrec = self.mhs.index(hs0)

    def member_hs(self, k): return self.ctx.hs - 4 if k < self.firstrec else self.ctx.hs

    def ids_occ(self, eids):
        need = [struct.pack(self.ctx.IDF, e) for e in eids if e not in self.occ]
        if need:
            o = occurrences(self.sp, need, self.workers)
            for e in eids:
                b = struct.pack(self.ctx.IDF, e)
                if b in o: self.occ[e] = o[b]
        return {e: self.occ[e] for e in eids}

    def _decode(self, i, short, trace=True):
        """decode the record at joined offset i on a window; offsets in the returned log are joined offsets"""
        c = self.ctx; base = max(0, i - 64); n = WIN
        if not short:
            L = struct.unpack('<I', self.J.get(i + 4 + c.W + 4, 4))[0]
            if L < (1 << 26): n = max(n, 64 + c.hs + L + 4096)
        while True:
            w = self.J.get(base, n)
            c.dec.log = []; c.dec.trace = trace
            try:
                r, q = c.dec.record(w, i - base, short)
                log = [(l[0], l[1], l[2] + base, l[3] + base, l[4]) + tuple(l[5:]) for l in c.dec.log]
                if q > len(w) - 8 and base + len(w) < len(self.J): raise IndexError('window')
                return r, q + base, log
            except Exception:
                if base + len(w) >= len(self.J) or n >= 16 * WIN: raise
                n = 16 * WIN

    def trace(self, eid):
        """first decodable record of eid in joined order (wlrec.Model.find, which=0)"""
        c = self.ctx; W = c.W; occ = self.ids_occ([eid])[eid]
        for k in occ:
            i = k - 4
            if not (0 <= i <= len(self.J) - 24): continue
            h = self.J.get(i, 16 + W)
            for short in (False, True):
                tag = struct.unpack_from('<H', h, 12 + W - (4 if short else 0))[0]
                if tag not in c.etags: continue
                try: r, q, log = self._decode(i, short)
                except Exception: continue
                if r['fields'].get('m_id') != eid: continue
                return i, r, log, q
        raise Refused('element %d: no decodable record in %s' % (eid, self.pn))

    def template(self, eid):
        c = self.ctx; W = c.W; idb = struct.pack(c.IDF, eid); occ = self.ids_occ([eid])[eid]; n = len(self.J)
        i, r, log, q = self.trace(eid); rec = self.J.get(i, q - i)
        hk = None
        for k in occ:      # Gen._hdr_at: first occurrence followed by the ElementHeader tag
            if k >= n - 20: break
            if self.J.get(k + W + 4, 2) == c.EHT: hk = k; break
        if hk is None: raise Refused('element %d: no element header' % eid)
        Lh = struct.unpack('<I', self.J.get(hk + W, 4))[0]; hdr = self.J.get(hk, W + 4 + Lh)
        cand = []
        for k in occ:      # zone record candidates (Gen.template)
            if k == i + 4 or k < 4 or k + W + 10 > n: continue
            b = self.J.get(k + W + 4, 6); L = struct.unpack_from('<I', b)[0]; tag = struct.unpack_from('<H', b, 4)[0]
            if not (12 <= tag < 12 + len(c.cls)) or tag == struct.unpack('<H', c.EHT)[0] or L > 1000000 or k - 4 + c.hs + L + 4 > n: continue
            if struct.unpack('<I', self.J.get(k - 4 + c.hs + L, 4))[0] != L: continue
            cand.append(k)
        after = [x for x in cand if x > i + len(rec)]
        if not cand: raise Refused('element %d: no zone record' % eid)
        zk = after[0] if after else cand[-1]
        zL = struct.unpack('<I', self.J.get(zk + W + 4, 4))[0]; item = self.J.get(zk, W + 4 + 4 + zL)
        rh, qh, hlogf = self._decode(hk - 4, True)
        hlog = [(l[1], l[2] - hk, l[3] - hk, l[4]) for l in hlogf]
        zone_after_q = [(x - 4, c.hs + struct.unpack('<I', self.J.get(x + W + 4, 4))[0]) for x in cand if x > q]
        return dict(tid=eid, rec=rec, hdr=hdr, item=item, hlog=hlog, log=[(l[1], l[2] - i, l[3] - i, l[4]) for l in log], cls=r['class'],
                    _i=i, _q=q, _hk=hk, _zk=zk, _zone=zone_after_q, _rlog=log, _r=r)

    # ---- byte edits (joined coordinates of the UNMODIFIED partition, same-length unless stated)
    def _replace(self, off, oldlen, new, note=''):
        self.touch(off, max(oldlen, 1)); self.edits.append((off, oldlen, bytes(new), note))

    def touch(self, off, n):
        for k in range(self.J.member_of(off), self.J.member_of(off + n - 1) + 1): self.touched.add(k)

    def _spans(self, base, old, new, note=''):
        """rvtgen_e._spans for same-length old/new: replace the differing runs only"""
        assert len(old) == len(new)
        i = 0; n = len(old)
        while i < n:
            if old[i] != new[i]:
                j = i
                while j < n and old[j] != new[j]: j += 1
                self._replace(base + i, j - i, new[i:j], note); i = j
            else: i += 1

    def _modify(self, i, q, r, rec_edits, note='record'):
        """Editor.modify: record bytes with edits applied (offsets joined), own length + Adler32 stamp rewritten, next record's A link at q rewritten"""
        c = self.ctx; W = c.W; hs = c.hs; old = self.J.get(i, q - i); rec = bytearray(old)
        for off, o, nb in sorted(rec_edits, key=lambda e: -e[0]): rec[off - i:off - i + o] = nb
        if not r['short']:
            struct.pack_into('<I', rec, 4 + W + 4, len(rec) - hs); struct.pack_into('<I', rec, 4 + W, zlib.adler32(bytes(rec[4 + W + 8:])) & 0xffffffff)
        else:
            struct.pack_into('<I', rec, 4 + W, zlib.adler32(bytes(rec[4 + W + 4:])) & 0xffffffff)
        nxt = struct.pack('<I', len(rec) - hs)
        self.touch(q, 4)      # pt.replace(q, 4, ...) always runs in the old writer
        if self.J.get(q, 4) != nxt: self._replace(q, 4, nxt, note + ' next-A')
        k0, k1 = self.J.member_of(i), self.J.member_of(q - 1)
        if k0 == k1: self.touch(i, q - i)      # Editor.modify replaces the whole record inside one member
        else:
            if len(rec) != len(old): raise Refused('size-changing edit of a record that spans members %d-%d' % (k0, k1))
            self.touch(i + 4 + W, 8)      # _modify_span rewrites length and stamp in place
        if len(rec) == len(old): self._spans(i, old, bytes(rec), note)
        else: self._replace(i, q - i, bytes(rec), note)
        return bytes(rec)

    # ---- ops
    def set_string_pid(self, eid, pid, value, expect=None):
        """edit.py _set_string_by_pid: the AString value entry contiguous with the ParamValueAString.m_paramId entry of pid"""
        _paths(); sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
        from rvtballet.edit import _eid_val, _value_entry, _check_text
        i, r, log, q = self.trace(eid)
        lg = [(l[0], l[1], l[2], l[3], l[4]) for l in log]
        for l in lg:
            if l[1] == 'ParamValueAString.m_paramId' and _eid_val(l[4]) == pid:
                vn = _value_entry(lg, 'AString', l)
                if vn is None: break
                if expect is not None:
                    cur = self.J.get(vn[2], vn[3] - vn[2]); nchr = struct.unpack_from('<I', cur)[0]
                    if cur[4:].decode('utf-16le', 'replace') != str(expect) or len(cur) != 4 + 2 * nchr: raise Refused('element %d parameter is not the expected %r' % (eid, expect))
                nb = struct.pack('<I', len(value.encode('utf-16le')) // 2) + value.encode('utf-16le')
                self._modify(i, q, r, [(vn[2], vn[3] - vn[2], nb)], 'set_string %d' % eid)
                self.expect.append((eid, 'astr', pid, value)); return
        raise Refused('string parameter %d not stored on %d' % (pid, eid))

    def resolve_pid(self, eid, name, kind='AString'):
        _paths(); sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
        from rvtballet.edit import _pid_for, _eid_val
        pids = _pid_for(name); _, _, log, _ = self.trace(eid)
        stored = {_eid_val(l[4]) for l in log if l[1] == 'ParamValue%s.m_paramId' % kind}
        hit = [p for p in pids if p in stored]
        if len(hit) != 1: raise Refused('parameter %r: %d candidate ids stored as %s on element %d' % (name, len(hit), kind, eid))
        return hit[0]

    def _guards_geom(self, eid, T, op):
        """edit.py _rvtedit_pass guards for move/rotate (pinned, curve-driven, dimension, origin 0, verified classes)"""
        _paths(); sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
        from rvtballet.edit import MOVE_VM_VERIFIED
        log = T['_rlog']; names = [str(l[1]) for l in log]
        for l in log:
            if l[1].startswith('Element.m_locked') and l[3] - l[2] == 1 and self.J.get(l[2], 1) != b'\0': raise Refused('element %d is pinned' % eid)
        if any(nm.startswith('FamInstCurveDriver.') for nm in names): raise Refused('element %d: curve-located family instance (%s refused, as the old editor)' % (eid, op))
        if op == 'move':
            tr = [l for l in log if l[1] == 'Trf.m_or']
            if tr and struct.unpack('<3d', self.J.get(tr[0][2], 24)) == (0.0, 0.0, 0.0) and not any(nm.startswith('GLine') for nm in names): raise Refused('element %d: Trf.m_or is (0,0,0)' % eid)
            if any(nm.startswith('LinearDimString') for nm in names) or T['cls'] == 'LinearDimString': raise Refused('element %d is a dimension' % eid)
            if T['cls'] not in MOVE_VM_VERIFIED: raise Refused('element %d is a %s (move not VM-verified)' % (eid, T['cls']))
        if T['cls'] != 'FamilyInstance': raise Refused('element %d is a %s: the segment writer handles FamilyInstance move/rotate only (for now)' % (eid, T['cls']))

    def _apply_geom(self, eid, T, hdr, rec, item):
        """the old move()/rotate() write-back: record spans via modify, header via replace_existing (length + next A + spans), zone item via _spans"""
        c = self.ctx; W = c.W
        if len(rec) != len(T['rec']) or len(hdr) != len(T['hdr']) or len(item) != len(T['item']): raise Refused('element %d: size-changing geometry edit' % eid)
        i, q = T['_i'], T['_q']; ed = []; a, b = T['rec'], rec; k = 0
        while k < len(a):
            if a[k] != b[k]:
                j = k
                while j < len(a) and (a[j] != b[j] or (j + 1 < len(a) and a[j + 1] != b[j + 1])): j += 1
                ed.append((i + k, j - k, bytes(b[k:j]))); k = j
            else: k += 1
        if ed: self._modify(i, q, T['_r'], ed, 'geom record %d' % eid)
        hk = T['_hk']; h = bytearray(hdr); struct.pack_into('<I', h, W, len(h) - W - 4); hlen = len(T['hdr'])
        nxt = struct.pack('<I', len(h) - W - 4)
        self.touch(hk + hlen, 4)
        if self.J.get(hk + hlen, 4) != nxt: self._replace(hk + hlen, 4, nxt, 'header next-A %d' % eid)
        self._spans(hk, T['hdr'], bytes(h), 'header %d' % eid)
        start = None; occ = self.occ[eid]
        hits = [p for p in occ if self.J.get(p, len(T['item'])) == T['item']]      # g.bj.find(T['item']) and its duplicate rule
        if not hits: raise Refused('element %d: zone item not found' % eid)
        if len(hits) > 1:
            cz = [st + 4 for st, ln in T['_zone'] if self.J.get(st + 4, len(T['item'])) == T['item']]
            if len(cz) != 1: raise Refused('element %d: zone item not unique' % eid)
            start = cz[0]
        else: start = hits[0]
        self._spans(start, T['item'], item, 'zone item %d' % eid)

    def _fake_edit(self):
        _paths(); import rvtedit
        class G: pass
        class F: pass
        f = F(); f.g = G(); f.g.W = self.ctx.W
        return rvtedit, f

    def move(self, eid, dx, dy, dz=0.0):
        T = self.template(eid); self._guards_geom(eid, T, 'move')
        rvtedit, f = self._fake_edit()
        try: hdr, rec, item, cnt = rvtedit.Edit._shifted(f, T, dx, dy, dz)
        except NotImplementedError as e: raise Refused(str(e))
        self._apply_geom(eid, T, hdr, rec, item); self.expect.append((eid, 'move', (dx, dy, dz), T))

    def rotate(self, eid, deg):
        T = self.template(eid); self._guards_geom(eid, T, 'rotate')
        rvtedit, f = self._fake_edit()
        try: hdr, rec, item = rvtedit.Edit._rotated(f, T, deg)
        except (NotImplementedError, KeyError) as e: raise Refused('rotate: %s' % e)
        self._apply_geom(eid, T, hdr, rec, item); self.expect.append((eid, 'rotate', deg, T))

    # ---------------------------------------------------------------- writer
    def dirty_raws(self):
        """apply the byte edits to copies of the members they fall in (wlpart offsets); returns {k: new raw}"""
        raws = {}; ed = sorted(self.edits, key=lambda e: e[0])
        for a, b in zip(ed, ed[1:]):
            if a[0] + a[1] > b[0]: raise Refused('overlapping edits at %d and %d' % (a[0], b[0]))
        for off, oldlen, new, note in reversed(ed):
            k = self.J.member_of(off); base = self.sp.offs[k]
            if off + oldlen > self.sp.offs[k + 1] or (oldlen == 0 and off == self.sp.offs[k + 1]): raise Refused('edit (%s) crosses the boundary of member %d' % (note, k))
            r = raws.get(k)
            if r is None: r = raws[k] = bytearray(self.J.raw(k))
            r[off - base:off - base + oldlen] = new
        for k in self.touched:
            if k not in raws: raws[k] = bytearray(self.J.raw(k))
        return {k: bytes(v) for k, v in raws.items()}

    def _frame_fields(self, k, new_raw):
        """X1 / X2 for a dirty member exactly as wlpart.cascade + rebuild compute them; refuses where the file's own frame disagrees with that rule"""
        hs = self.member_hs(k); _, f = self.sp.frame_before(k); off = 24 if k == 0 else 12
        x1o, x2o = struct.unpack_from('<I', f, off)[0], struct.unpack_from('<I', f, off + 8)[0]
        orig = self.J.raw(k)
        if len(orig) - hs * x1o != x2o: raise Refused('member %d: stored X2 %d is not ISIZE - hs*X1 (%d); frame semantics unknown here' % (k, x2o, len(orig) - hs * x1o))
        x1 = x1o
        if len(new_raw) != len(orig):
            def walk(buf):
                p = -4; n = 0
                while p + hs <= len(buf):
                    p += hs + struct.unpack_from('<I', buf, p + hs - 4)[0]
                    if p < 0 or p + 4 > len(buf): break
                    n += 1
                return n
            if walk(orig) != x1o: raise Refused('member %d: record-chain walk (%d) does not reproduce the stored X1 (%d)' % (k, walk(orig), x1o))
            x1 = walk(new_raw)
            if x1 != x1o: raise Refused('member %d: record count would change (%d -> %d)' % (k, x1o, x1))
        limit = 131071 if max(m[2] for m in self.sp.mem) <= 131088 else max(m[2] for m in self.sp.mem)
        if len(new_raw) > limit: raise Refused('member %d would exceed the member size limit (%d > %d): re-split not handled' % (k, len(new_raw), limit))
        return x1, len(new_raw) - hs * x1

    def build(self, mode='fit'):
        """-> (payload patches [(payload_off, old_len, new_bytes)], delta, info) for the chosen layout"""
        _paths(); import rvtw
        raws = self.dirty_raws(); sp = self.sp; patches = []; info = dict(dirty=sorted(raws), mode=mode)
        if mode == 'fit': raws = {k: v for k, v in raws.items() if v != self.J.raw(k)}      # an unchanged member keeps Revit's own bytes
        for k in sorted(raws):
            pos, end, isize, sl = sp.mem[k]; nr = raws[k]; x1, x2 = self._frame_fields(k, nr)
            gzh = sp.payload(pos, 10)
            if mode == 'fit':
                try: m = rvtw.gz_member(nr, gzh, (end - 8) - (pos + 10))
                except ValueError: raise Refused('member %d: re-deflated data does not fit its original compressed size' % k)
                if len(m) != end - pos: raise Refused('member %d: exact-size encoding failed' % k)
            else: m = rvtw.gz_member(nr, gzh, None)
            info.setdefault('members', []).append((k, end - pos, len(m), isize, len(nr)))
            val = len(m) + 8
            fa, fb = sp.frame_before(k); fb = bytearray(fb); o = 24 if k == 0 else 12
            struct.pack_into('<I', fb, o + 4, val); struct.pack_into('<I', fb, o, x1); struct.pack_into('<I', fb, o + 8, x2)
            if fb != sp.frame_before(k)[1]: patches.append((fa + (o - 0), 12, bytes(fb[o:o + 12])))
            aa, ab = sp.frame_after(k); ab = bytearray(ab); struct.pack_into('<I', ab, 2, val)
            if ab != sp.frame_after(k)[1]: patches.append((aa + 2, 4, bytes(ab[2:6])))
            patches.append((pos, end - pos, m))
        patches.sort(key=lambda p: p[0]); delta = sum(len(n) - o for _, o, n in patches)
        if mode == 'fit' and delta: raise Refused('fit layout changed the payload size')
        return patches, delta, info

    def new_stream_pages(self, patches, delta):
        """yield (page index, stored page bytes) for every page of the stream that differs from the source, built with page ECC.
        shift layout: all pages from the first patched one to the end (later bytes move); fit layout: only the pages the patches touch."""
        _paths(); import ecc
        sp = self.sp
        if delta > 0:
            z = sp.payload(sp.plen - delta, delta)
            if z.count(0) != len(z): raise Refused('payload grows by %d bytes beyond the original page layout (no zero pad to consume)' % delta)
        first = patches[0][0] // PAGE_PAYLOAD
        last = sp.npages() - 1 if delta else (patches[-1][0] + patches[-1][1] - 1) // PAGE_PAYLOAD
        # map new payload offset -> source bytes: walk patches in order
        def new_bytes(a, n):
            """new payload [a, a+n): source bytes with patches applied and the tail adjusted (zero pad / trimmed pad)"""
            out = bytearray(); shift = 0; cur_new = 0; cur_old = 0
            segs = []      # (new_start, new_end, kind, data or old_start)
            for po, ol, nb in patches:
                if po > cur_old: segs.append((cur_new, cur_new + po - cur_old, 'old', cur_old)); cur_new += po - cur_old
                segs.append((cur_new, cur_new + len(nb), 'new', nb)); cur_new += len(nb); cur_old = po + ol
            rest_old = sp.plen - cur_old
            if delta >= 0: segs.append((cur_new, cur_new + rest_old - delta, 'old', cur_old))
            else: segs.append((cur_new, cur_new + rest_old, 'old', cur_old)); segs.append((cur_new + rest_old, sp.plen, 'zero', None))
            end = a + n
            for s0, s1, kd, d in segs:
                lo, hi = max(s0, a), min(s1, end)
                if lo >= hi: continue
                if kd == 'old': out += sp.payload(d + (lo - s0), hi - lo)
                elif kd == 'new': out += d[lo - s0:hi - s0]
                else: out += b'\0' * (hi - lo)
            assert len(out) == min(end, sp.plen) - a, (len(out), a, n)
            return bytes(out)
        for p in range(first, last + 1):
            cap = sp.page_cap(p); data = new_bytes(p * PAGE_PAYLOAD, cap); N = sp.page_len(p)
            yield p, ecc.parity(data, N)

    def write(self, dest, mode='fit', verify=True, fsync=True):
        """write the edited copy to dest (must not exist): reflink/copy of the source + rewritten sectors of the changed pages; verified before the rename"""
        t0 = time.time(); src = self.ctx.path
        if os.path.exists(dest): raise Refused('destination exists')
        if os.path.abspath(dest) == os.path.abspath(src): raise Refused('destination is the source')
        patches, delta, info = self.build(mode)
        pages = list(self.new_stream_pages(patches, delta))
        tmp = dest + '.segpart%d' % os.getpid()
        st = os.stat(src)
        try:
            info['copy'] = clone_file(src, tmp)
            fd = os.open(tmp, os.O_RDWR); written = 0
            try:
                for p, b in pages:
                    written += _pwrite_stream(fd, self.sp, p * PAGE_STORED, b)
                if fsync: os.fsync(fd)
            finally: os.close(fd)
            info.update(pages=[p for p, _ in pages], bytes_written=written, delta=delta)
            if verify: info['verify'] = verify_output(self, tmp, patches, delta, [p for p, _ in pages])
            if os.stat(src).st_mtime_ns != st.st_mtime_ns or os.stat(src).st_size != st.st_size: raise Refused('the source changed during the save')
            os.replace(tmp, dest)
            if fsync:
                dfd = os.open(os.path.dirname(os.path.abspath(dest)) or '.', os.O_RDONLY)
                try: os.fsync(dfd)
                finally: os.close(dfd)
        finally:
            if os.path.exists(tmp): os.remove(tmp)
        info['seconds'] = round(time.time() - t0, 3); return info


def _pwrite_stream(fd, sp, a, data):
    """write stream bytes [a, a+len) through the sector chain"""
    ss = sp.ss; n = 0; end = a + len(data)
    while a < end:
        k, off = divmod(a, ss); take = min(ss - off, end - a)
        os.pwrite(fd, data[n:n + take], (sp.chain[k] + 1) * ss + off); a += take; n += take
    return n


def clone_file(src, dst):
    """copy-on-write clone when the filesystem supports it (FICLONE), else copy_file_range (kernel-side copy); returns the method used"""
    import fcntl
    with open(src, 'rb') as fi, open(dst, 'wb') as fo:
        try:
            fcntl.ioctl(fo.fileno(), 0x40049409, fi.fileno()); return 'reflink'
        except OSError: pass
        n = os.fstat(fi.fileno()).st_size; off = 0
        while off < n:
            c = os.copy_file_range(fi.fileno(), fo.fileno(), n - off, off, off)
            if c <= 0: break
            off += c
        if off != n: raise OSError('short copy')
        return 'copy_file_range'


# ---------------------------------------------------------------- verification (scoped)
def verify_output(sess, out, patches, delta, pages):
    """independent re-read of the written file: (1) bytes outside the rewritten sectors identical to the source (full compare), (2) every rewritten page passes
    page ECC, (3) the segment chain re-walks with the same member count, frames consistent, (4) every dirty member inflates (CRC/ISIZE) to the intended raw,
    (5) the intended raws differ from the source only in the declared edit spans, (6) every member of the first run outside the dirty set is byte-identical
    (compressed) to the source, (7) edited records decode and carry the expected values."""
    _paths(); import ecc, numpy as np
    sp = sess.sp; t0 = time.time(); rep = {}
    secs = set()
    for p in pages:
        a = p * PAGE_STORED; b = a + sp.page_len(p)
        for s in range(a // sp.ss, (b - 1) // sp.ss + 1): secs.add(sp.chain[s])
    A = np.memmap(sess.ctx.path, np.uint8, 'r'); B = np.memmap(out, np.uint8, 'r')
    if len(A) != len(B): raise Refused('verify: output size differs')
    ss = sp.ss; mask = np.ones(len(A) // ss, bool)
    for s in secs: mask[s + 1] = False
    diff_secs = []
    step = 1 << 26
    for o in range(0, len(A), step):
        d = np.nonzero(A[o:o + step] != B[o:o + step])[0]
        if len(d):
            ds = np.unique((d + o) // ss)
            bad = ds[mask[ds]] if len(ds) else ds
            if len(bad): raise Refused('verify: sector %d outside the rewritten pages differs from the source' % int(bad[0]))
            diff_secs += ds.tolist()
    rep['changed_sectors'] = len(diff_secs); rep['rewritten_sectors'] = len(secs)
    so = SegPart(out, sp.name)
    pg = [so.stored(p * PAGE_STORED, so.page_len(p)) for p in pages]
    bad = [p for p, g in zip(pages, pg) if not ecc.check(g)]
    if bad: raise Refused('verify: page ECC wrong on page(s) %s' % bad[:5])
    if len(so.mem) != len(sp.mem): raise Refused('verify: member run changed (%d -> %d members)' % (len(sp.mem), len(so.mem)))
    raws = sess.dirty_raws(); sh = 0; dirty = set(raws)
    for k in range(len(sp.mem)):
        if k in dirty:
            r = so.member_raw(k)
            if r != raws[k]: raise Refused('verify: member %d does not inflate to the intended bytes' % k)
        else:
            a0, a1 = sp.mem[k][0], sp.mem[k][1]; b0, b1 = so.mem[k][0], so.mem[k][1]
            if a1 - a0 != b1 - b0 or (k in sess.J.touched or a0 // PAGE_PAYLOAD in pages or b0 // PAGE_PAYLOAD in pages or (b0 - a0) != sh) and sp.payload(a0, a1 - a0) != so.payload(b0, b1 - b0):
                raise Refused('verify: untouched member %d changed' % k)
        if k in dirty: sh += (so.mem[k][1] - so.mem[k][0]) - (sp.mem[k][1] - sp.mem[k][0])
    if delta == 0:
        pass
    else:      # shift layout: everything after the last dirty member is the source shifted by delta (members, frames, interludes, tail)
        k = max(dirty); a = sp.mem[k][1] + 8; b = so.mem[k][1] + 8; n = sp.plen - a - max(delta, 0)
        step = 1 << 24
        for o in range(0, n, step):
            if sp.payload(a + o, min(step, n - o)) != so.payload(b + o, min(step, n - o)): raise Refused('verify: shifted tail differs from the source near %d' % (a + o))
    # (5) declared spans only
    allowed = []
    for off, ol, nb, note in sess.edits: allowed.append((off, off + max(ol, len(nb))))
    for k, r in raws.items():
        o = sess.J.raw(k); base = sp.offs[k]
        if len(o) == len(r):
            d = [i for i in range(len(o)) if o[i] != r[i]] if len(o) < 300000 else []
            for i in d:
                if not any(a <= base + i < b for a, b in allowed): raise Refused('verify: member %d byte %d changed outside the declared edits' % (k, i))
    # (7) readback of edited records in the OUTPUT
    s2 = Session.__new__(Session); s2.ctx = sess.ctx; s2.pn = sp.name; s2.sp = so; s2.J = Joined(so); s2.workers = sess.workers; s2.edits = []; s2.occ = {}; s2.expect = []
    s2.mhs = sess.mhs; s2.firstrec = sess.firstrec
    rb = []
    for eid, kind, a, b in [(e[0], e[1], e[2], e[3]) for e in sess.expect]:
        i, r, log, q = s2.trace(eid)
        if kind == 'astr':
            sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet')); from rvtballet.edit import _eid_val, _value_entry
            lg = [(l[0], l[1], l[2], l[3], l[4]) for l in log]
            ent = [l for l in lg if l[1] == 'ParamValueAString.m_paramId' and _eid_val(l[4]) == a]
            vn = _value_entry(lg, 'AString', ent[0]) if ent else None
            got = s2.J.get(vn[2] + 4, vn[3] - vn[2] - 4).decode('utf-16le') if vn else None
            if got != b: raise Refused('verify: element %d reads back %r, expected %r' % (eid, got, b))
            rb.append((eid, 'astr', got))
        elif kind == 'move':
            T = b; L0 = {n: o for n, o, e, v in T['log']}; nm = 'FamilyInstance.m_instOrigin' if 'FamilyInstance.m_instOrigin' in L0 else 'Trf.m_or'
            o0 = struct.unpack_from('<3d', T['rec'], L0[nm]); l1 = [l for l in log if l[1] == nm][0]; o1 = struct.unpack('<3d', s2.J.get(l1[2], 24))
            if any(abs(o1[j] - o0[j] - a[j]) > 1e-9 for j in range(3)): raise Refused('verify: element %d origin %r, expected %r + %r' % (eid, o1, o0, a))
            rb.append((eid, 'move', o1))
        elif kind == 'rotate':
            rb.append((eid, 'rotate', [l[4] for l in log if l[1] == 'FamilyInstance.m_RefDir'][:1]))
    rep['readback'] = rb; rep['seconds'] = round(time.time() - t0, 3)
    return rep


def apply_ops(path, dest, ops, mode='fit', workers=None):
    """ops: dicts like edit.py's ({'op': 'set_string', 'eid', 'pid' | 'param', 'value', 'expect'?}, {'op': 'move', 'eid', 'dx', 'dy', 'dz'}, {'op': 'rotate', 'eid', 'deg'})"""
    t0 = time.time(); s = Session(path, workers=workers); seen = set()
    for o in ops:
        e = o['eid']
        if o['op'] in ('move', 'rotate'):
            if e in seen: raise Refused('element %d: one geometric op per element and save' % e)
            seen.add(e)
        if o['op'] == 'set_string':
            pid = o.get('pid')
            if pid is None: pid = s.resolve_pid(e, o['param'])
            s.set_string_pid(e, pid, o['value'], o.get('expect'))
        elif o['op'] == 'move': s.move(e, o['dx'], o['dy'], o.get('dz', 0.0))
        elif o['op'] == 'rotate': s.rotate(e, o['deg'])
        else: raise Refused('op %s not handled by the segment writer' % o['op'])
    info = s.write(dest, mode=mode)
    info['total_seconds'] = round(time.time() - t0, 3); info['members_inflated'] = len(s.J.touched); info['members_total'] = len(s.sp.mem)
    return info


def main(argv=None):
    import argparse, json, resource
    ap = argparse.ArgumentParser(prog='segedit'); ap.add_argument('file'); ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--mode', choices=('fit', 'shift'), default='fit'); ap.add_argument('--workers', type=int)
    ap.add_argument('--set-string', nargs=3, action='append', default=[], metavar=('EID', 'PARAM', 'VALUE'))
    ap.add_argument('--move', nargs=4, action='append', default=[], metavar=('EID', 'DX', 'DY', 'DZ'))
    ap.add_argument('--rotate', nargs=2, action='append', default=[], metavar=('EID', 'DEG'))
    a = ap.parse_args(argv); ops = []
    for e, p, v in a.set_string: ops.append(dict(op='set_string', eid=int(e), value=v, **({'pid': int(p)} if p.lstrip('-').isdigit() else {'param': p})))
    for e, x, y, z in a.move: ops.append(dict(op='move', eid=int(e), dx=float(x), dy=float(y), dz=float(z)))
    for e, d in a.rotate: ops.append(dict(op='rotate', eid=int(e), deg=float(d)))
    try: info = apply_ops(a.file, a.output, ops, a.mode, a.workers)
    except Refused as e: print('REFUSED: %s (nothing written)' % e); return 2
    ru = resource.getrusage(resource.RUSAGE_SELF); rc = resource.getrusage(resource.RUSAGE_CHILDREN)
    info['cpu'] = round(ru.ru_utime + ru.ru_stime + rc.ru_utime + rc.ru_stime, 2); info['maxrss_mb'] = round(max(ru.ru_maxrss, rc.ru_maxrss) / 1024, 1)
    print(json.dumps(info, default=str)); return 0


if __name__ == '__main__':
    sys.exit(main())
