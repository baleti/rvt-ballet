"""A source whose CFB container is damaged in ways olefile reads silently (ElemTable size cut in the directory, MiniFAT header byte, a renamed stream, a FAT entry shared by two chains) must be refused by SAVE AS with no edits queued: 4xx, nothing written. Autodesk 2024 template."""
import os, sys, struct, asyncio, tempfile, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server
import olefile
def variants():
    d0 = open(SRC, 'rb').read(); o = olefile.OleFileIO(SRC); ss = o.sectorsize; per = ss // 4
    s = o.first_dir_sector; ch = []
    while s < 0xFFFFFFFA and s not in ch: ch.append(s); s = o.fat[s]
    off = lambda i: (ch[(i * 128) // ss] + 1) * ss + (i * 128) % ss
    idx = lambda name: next(k for k, e in enumerate(o.direntries) if e is not None and e.entry_type == 2 and e.name == name)
    d = bytearray(d0); i = idx('ElemTable'); struct.pack_into('<Q', d, off(i) + 120, struct.unpack_from('<Q', d, off(i) + 120)[0] - 4096); yield 'elemtable_cut', d
    d = bytearray(d0); d[63] ^= 0x04; yield 'minifat_hdr', d
    d = bytearray(d0); a, b = idx('Contents'), idx('TransmissionData'); d[off(b):off(b) + 66] = d[off(a):off(a) + 66]; yield 'dup_name', d
    big = max((e for e in o.direntries if e is not None and e.entry_type == 2), key=lambda e: e.size)
    c = [big.isectStart]
    while len(c) < 200: c.append(o.fat[c[-1]])
    sec = c[50]; fs = struct.unpack_from('<I', d0, 76 + 4 * (sec // per))[0]
    d = bytearray(d0); struct.pack_into('<I', d, (fs + 1) * ss + 4 * (sec % per), c[46]); yield 'fat_loop', d
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    bad = []
    for name, data in [v for v in variants() if v[0] == ONLY]:
        md = os.path.join(_T, 'm_' + name); os.makedirs(md); src = os.path.join(_T, name + '.rte'); open(src, 'wb').write(data)
        out = os.path.join(_T, 'out_' + name + '.rte')
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            r = await c.post('/api/m/m/saveas', json={'dest': out}); st = r.status
        print(name, st, flush=True)
        if st < 400 or st >= 500 or os.path.exists(out): bad.append((name, st, os.path.exists(out)))
    assert not bad, bad
NAMES = ('elemtable_cut', 'minifat_hdr', 'dup_name', 'fat_loop')
ONLY = sys.argv[1] if len(sys.argv) > 1 else None
if ONLY:
    asyncio.run(run())        # one variant per process: the decoded model of each variant stays in memory (4 GB after three of them)
else:
    import subprocess
    for n in NAMES:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), n]); assert r.returncode == 0, n
    print('OK damaged containers refused by SAVE AS, nothing written')
