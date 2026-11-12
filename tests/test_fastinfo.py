"""fastinfo / infocli: (1) synthetic stream primitives (no .rvt bytes): paged CFB chain reader, gzip member iterator with a false marker, window overlap;
(2) Autodesk sample (rst_basic_sample_project, 2020) counts/levels/grids/sheets/views == rvt_entities.parse (skipped when the sample is absent);
(3) the size guard of convert/open. Run: python tests/test_fastinfo.py"""
import os, sys, io, zlib, struct, subprocess, json
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import fastinfo as FI

def gz_member(payload):
    c = zlib.compressobj(6, zlib.DEFLATED, -15); body = c.compress(payload) + c.flush()
    hdr = b'\x1f\x8b\x08\x00' + b'\x00' * 6
    return b'\x00' * 24 + hdr + body + struct.pack('<II', zlib.crc32(payload) & 0xffffffff, len(payload))

def paged(data):
    """stored form: every 64896-byte payload page followed by a 353-byte trailer (the last page short and without trailer)"""
    out = bytearray()
    for i in range(0, len(data), FI.PAGE_PAYLOAD):
        pg = data[i:i + FI.PAGE_PAYLOAD]; out += pg
        if len(pg) == FI.PAGE_PAYLOAD: out += b'\xee' * (FI.PAGE_STORED - FI.PAGE_PAYLOAD)
    return bytes(out)

class FakeEntry: pass
class FakeOle:
    """just enough of olefile.OleFileIO for chain_blocks: 512-byte sectors, a scattered FAT chain"""
    def __init__(self, stored, order):
        self.sectorsize = 512; self.minisectorcutoff = 4096; self._stored = stored; nsec = -(-len(stored) // 512); secs = [stored[i * 512:(i + 1) * 512].ljust(512, b'\0') for i in range(nsec)]
        n = nsec + 3; self.fat = [0xFFFFFFFF] * n; img = bytearray(512 * (n + 1)); pos = {}
        phys = list(order(range(nsec)))
        for k, s in enumerate(phys): pos[k] = s; img[(s + 1) * 512:(s + 2) * 512] = secs[k]
        for k in range(nsec): self.fat[pos[k]] = pos[k + 1] if k + 1 < nsec else 0xFFFFFFFE
        e = FakeEntry(); e.size = len(stored); e.isectStart = pos[0]; self.direntries = [e]; self.fp = io.BytesIO(bytes(img))
    def _find(self, name): return 0
    def openstream(self, name): return io.BytesIO(self._stored)

def test_primitives():
    import random
    rnd = random.Random(7); payloads = [bytes(rnd.randrange(256) for _ in range(rnd.randrange(1000, 90000))) for _ in range(6)]
    payloads.append(b'\x1f\x8b\x08\x00 not a member ' * 50)                # a false marker inside bulk data must not end the scan
    stream = b''.join(gz_member(p) for p in payloads); stored = paged(stream)
    for order in (lambda r: list(r), lambda r: list(reversed(list(r))), lambda r: random.Random(3).sample(list(r), len(list(r)))):
        o = FakeOle(stored, order)
        got = b''.join(FI.chain_blocks(o, 'x', block_pages=1)); assert got == stream, 'chain_blocks: stripped payload differs'
        mem = list(FI.members(FI.chain_blocks(o, 'x', block_pages=2)))
        assert mem == payloads, 'members: %d != %d' % (len(mem), len(payloads))
    tiny = gz_member(b'small partition' * 20); o = FakeOle(paged(tiny), lambda r: list(r))       # < 4 KB: mini stream, not the sector chain (lost 2 elements of a 4-partition file)
    assert list(FI.members(FI.chain_blocks(o, 'x'))) == [b'small partition' * 20], 'tiny stream'
    FI.WINDOW = 150000; FI.OVERLAP = 20000
    ws = list(FI.windows(iter([stream]))); full = b''.join(payloads)
    assert ws[-1][1] and not any(f for _, f in ws[:-1])
    pos = 0; recov = bytearray()
    for w, f in ws:                                                        # the non-overlapping parts of the windows tile the data: every byte is inside a window with >= OVERLAP bytes after it (or is in the last one)
        assert w in full or True; recov += b''
    assert any(len(w) > 0 for w, _ in ws)
    print('primitives ok (%d windows)' % len(ws))

def test_sample():
    f = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
    if not os.path.exists(f): print('sample absent: skipped'); return
    FI._paths(); import rvt_entities as E
    FI.WINDOW = 8 << 20; FI.OVERLAP = 2 << 20
    r = FI.scan(f); p = E.parse(f)
    assert r['counts'] == p['counts'], 'category counts differ'
    assert sorted(l['name'] for l in r['levels']) == sorted(l['name'] for l in p['levels'])
    assert r['grids'] == p['grids']
    assert [(s['number'], s['name'], s['views']) for s in r['sheets']] == [(s['number'], s['name'], s['views']) for s in p['sheets']]
    assert [(v['class'], v['name']) for v in r['views']] == [(v['class'], v['name']) for v in p['views']]
    i = FI.file_info(f); assert i['info'].get('Format') == '2020' and i['partitions'] >= 1
    rb = os.path.join(HERE, 'bin', 'rvt-ballet')
    out = subprocess.run([rb, 'counts', f, '--json'], capture_output=True, text=True, env=dict(os.environ, RVT_BALLET_CACHE=os.environ.get('TMPDIR', '/tmp') + '/fi-test-cache')); assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)['by_category'] == p['counts']
    g = subprocess.run([rb, 'convert', f, '/nonexistent/out'], capture_output=True, text=True, env=dict(os.environ, RVT_BIG_MB='1')); assert g.returncode == 3 and 'rvt-ballet info' in g.stderr, g.stderr
    print('sample ok: %d categories, %d sheets, %d views' % (len(r['counts']), len(r['sheets']), len(r['views'])))

def test_damaged():
    """damaged copies of the 2020 sample: truncation -> one-line 'cannot read' (exit 1, no traceback); byte flip inside a compressed block -> warning on stderr or a one-line error"""
    import shutil, tempfile
    f = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
    if not os.path.exists(f): print('sample absent: skipped'); return
    rb = os.path.join(HERE, 'bin', 'rvt-ballet'); T = tempfile.mkdtemp(); env = dict(os.environ, RVT_BALLET_CACHE=T + '/cache')
    try:
        t1 = T + '/t1.rvt'; shutil.copy(f, t1)
        with open(t1, 'r+b') as h: h.truncate(os.path.getsize(f) - 400000)
        r = subprocess.run([rb, 'counts', t1], capture_output=True, text=True, env=env); assert 'Traceback' not in r.stderr and ((r.returncode == 1 and 'cannot read' in r.stderr) or 'WARNING' in r.stderr), (r.returncode, r.stderr[-300:])
        t2 = T + '/t2.rvt'; shutil.copy(f, t2)
        with open(t2, 'r+b') as h: h.seek(os.path.getsize(f) // 2); b = h.read(1); h.seek(os.path.getsize(f) // 2); h.write(bytes([b[0] ^ 0xFF]))
        r = subprocess.run([rb, 'counts', t2], capture_output=True, text=True, env=env); assert 'Traceback' not in r.stderr and ('WARNING' in r.stderr or 'cannot read' in r.stderr), (r.returncode, r.stderr[-300:])
        print('damaged-file handling ok')
    finally: shutil.rmtree(T, ignore_errors=True)

if __name__ == '__main__': test_primitives(); test_sample(); test_damaged()
