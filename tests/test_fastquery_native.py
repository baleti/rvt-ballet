"""fastquery channel split + native framing: synthetic channel-102 runs (no .rvt bytes). Python frame_records and the C helper (_rvtframe.so, skipped when
absent) must agree; resync mid-run, 24-byte terminator, chain mismatch -> fallback (None), weak candidate -> fallback, native gzip CRC flag, and channel
values outside 101/102/103 (walk keeps every segment, 3-tuples). Run: python -m pytest tests/test_fastquery_native.py"""
import os, sys, struct, zlib, random
import numpy as np
import pytest
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import fastquery as Q

NT = 40            # schema size: tags 12..39 valid


@pytest.fixture(autouse=True, params=[8, 4], ids=['W8', 'W4'])
def _globals(request):
    global W; W = request.param
    old = {k: Q._G.get(k) for k in ('cls', 'ids', 'id_top')}
    Q._G['cls'] = [None] * (NT - 12); Q._G['ids'] = np.arange(1, 100000, dtype=np.uint64); Q._G.pop('id_top', None)
    yield
    for k, v in old.items():
        if v is None: Q._G.pop(k, None)
        else: Q._G[k] = v
    Q._G.pop('id_top', None)


W = 8     # id width under test (parametrized below: 8 = Revit 2024+, 4 = 2018-2023)


def rec(eid, tag, body=b'', x=7):
    """one 102 record WITHOUT its leading prefix: [id: W bytes][u32 x][u32 L][u16 tag][body]; L counts from the tag"""
    L = 2 + len(body); return (eid.to_bytes(W, 'little') if eid >= 0 else b'\xff' * W) + struct.pack('<II', x, L) + struct.pack('<H', tag) + body, L


def run_bytes(recs, terminator=False, lead=b''):
    """a run: 8-byte pad (its last 4 bytes stand in for the first record's missing prefix word), the records each preceded by the previous length, then the
    closing prefix (4 bytes) or the 24-byte id=-1 terminator. lead = bytes between the pad and the first prefix (mid-run start)."""
    out = bytearray(8) + lead; prev = 0; pos = []
    for eid, tag, body in recs:
        r, L = rec(eid, tag, body); pos.append(len(out)); out += struct.pack('<I', prev) + r; prev = L
    if terminator: out += struct.pack('<I', prev) + b'\xff' * W + struct.pack('<II', 1, 0) + bytes(4)
    else: out += struct.pack('<I', prev)
    return bytes(out), pos


def frame(chunk, sizes=None, nmain=None):
    sizes = sizes or [len(chunk)]; segs = [(1000 * (i + 1), 50, sz, 102) for i, sz in enumerate(sizes)]
    return Q.frame_records(chunk, sizes, segs, nmain or len(sizes), W)


def mk(n=12, seed=1, ids=None):
    rnd = random.Random(seed)
    return [((ids[i] if ids else 100 + 3 * i), rnd.randint(12, NT - 1), bytes(rnd.randrange(256) for _ in range(rnd.randint(0, 90)))) for i in range(n)]


def ids_tags(fr): return [(e, t) for (_, _, e, t) in fr]


def test_clean_run_and_terminator():
    for term in (False, True):
        recs = mk(); chunk, _ = run_bytes(recs, terminator=term)
        assert ids_tags(frame(chunk)) == [(e, t) for e, t, _ in recs], term


def test_resync_mid_run():
    recs = mk(15, 2); chunk, _ = run_bytes(recs, lead=bytes(37))
    fr = frame(chunk); assert fr is not None and ids_tags(fr) == [(e, t) for e, t, _ in recs]


def test_chain_mismatch_falls_back():
    recs = mk(12, 3); chunk, pos = run_bytes(recs); b = bytearray(chunk)
    b[pos[8]:pos[8] + 4] = struct.pack('<I', 5)          # a broken prefix word after the verified start: the hop check refuses (None -> the caller uses the old scan)
    assert frame(bytes(b)) is None


def test_weak_candidate_falls_back():
    r, L = rec(500, 20, bytes(20)); chunk = bytes(8) + struct.pack('<I', 0) + r[:-10]      # one record running past the chunk end cannot be verified
    fr = frame(chunk); assert fr is None or fr == []


def test_tag_out_of_schema_falls_back():
    recs = mk(8, 4); chunk, pos = run_bytes(recs); b = bytearray(chunk)
    b[pos[6] + 8 + W + 4:pos[6] + 8 + W + 6] = struct.pack('<H', NT + 5)       # after the verified start (resync skips a bad start by design)
    assert frame(bytes(b)) is None


def test_only_main_part_records_are_returned():
    recs = mk(20, 5); c1, _ = run_bytes(recs[:10]); c2, _ = run_bytes(recs[10:])
    fr = frame(c1 + c2, [len(c1), len(c2)], 1)
    assert [e for _, _, e, _ in fr] == [e for e, _, _ in recs[:10]]


@pytest.fixture
def nat():
    so = os.path.join(HERE, 'rvtballet', '_rvtframe.so')
    if not os.path.exists(so) or Q._libdeflate() is None: pytest.skip('no _rvtframe.so / libdeflate')
    import ctypes as C
    L = C.CDLL(so); L.frame102.restype = C.c_int64; P = C.c_void_p; I = C.c_int64
    L.frame102.argtypes = [P, I, P, I, I, P, C.c_int, C.c_uint64, C.c_int, P, I]; return L


def c_frame(L, chunk, sizes, nmain):
    bounds = np.zeros(len(sizes) + 1, np.int64); np.cumsum(sizes, out=bounds[1:])
    sa = np.array([(1000 * (i + 1), 50) for i in range(len(sizes))], np.int64)
    buf = np.frombuffer(chunk, np.uint8).copy(); out = np.empty(4 * (len(chunk) // 20 + 64), np.int64)
    k = L.frame102(buf.ctypes.data, len(chunk), bounds.ctypes.data, len(sizes), nmain, sa.ctypes.data, NT, Q._id_top(), W, out.ctypes.data, len(out) // 4)
    return None if k < 0 else [tuple(r) for r in out[:4 * k].reshape(-1, 4).tolist()]


def test_c_equals_python(nat):
    for seed in range(20):
        n = 10 + seed; recs = mk(n, seed, ids=[50 + 7 * i for i in range(n)])
        chunk, _ = run_bytes(recs, terminator=bool(seed % 2), lead=bytes(seed * 3 % 40))
        py = frame(chunk); c = c_frame(nat, chunk, [len(chunk)], 1)
        assert py is not None and c is not None and [tuple(x) for x in py] == c, seed


def test_c_refuses_what_python_refuses(nat):
    recs = mk(12, 3); chunk, pos = run_bytes(recs); b = bytearray(chunk)
    b[pos[8]:pos[8] + 4] = struct.pack('<I', 5)
    assert frame(bytes(b)) is None and c_frame(nat, bytes(b), [len(b)], 1) is None


def stored_segment(payload):
    c = zlib.compressobj(6, zlib.DEFLATED, -15); body = c.compress(payload) + c.flush()
    gz = bytes.fromhex('1f8b080000000000000b') + body + struct.pack('<II', zlib.crc32(payload) & 0xffffffff, len(payload))
    return gz + bytes(8), len(gz) + 8


def test_c_inflate_task_crc_flag(nat, tmp_path):
    """C inflate_task: good segments inflate with bad[i]=0; a segment whose stored CRC32 is wrong inflates but is flagged"""
    import ctypes as C, mmap
    ld = Q._libdeflate()[0]; P = C.c_void_p; I = C.c_int64
    nat.set_fd.restype = I; nat.set_fd.argtypes = [I]; nat.set_fd(-1)      # mmap mode: the helper keeps the fd of an earlier pread-mode test
    nat.inflate_task.restype = I; nat.inflate_task.argtypes = [P, I, P, I, I, P, I, P, I, P, P, I, P, P, P, P]
    pays = [bytes(random.Random(i).randrange(256) for _ in range(3000)) for i in range(3)]
    st = [stored_segment(p) for p in pays]
    data = b''.join(s for s, _ in st); lens = [l for _, l in st]; offs = [sum(lens[:i]) for i in range(3)]
    b = bytearray(data); b[offs[1] + lens[1] - 16] ^= 0xff
    ss = 512; img = bytes(ss) + bytes(b); nsec = -(-len(img) // ss); img = img.ljust(nsec * ss, b'\0')
    f = tmp_path / 'img.bin'; f.write_bytes(img)
    fd = os.open(str(f), os.O_RDONLY); mm = mmap.mmap(fd, 0, prot=mmap.PROT_READ); os.close(fd)
    mv = np.frombuffer(mm, np.uint8); chain = np.arange(nsec - 1, dtype=np.int32)
    sa = np.array([(offs[i], lens[i]) for i in range(3)], np.int64); out = np.zeros(20000, np.uint8); sizes = np.zeros(3, np.int64)
    tmp = np.zeros(1 << 16, np.uint8); bad = np.zeros(3, np.uint8)
    dec = ld.libdeflate_alloc_decompressor(); fnp = C.cast(ld.libdeflate_deflate_decompress_ex, C.c_void_p).value; crcp = C.cast(ld.libdeflate_crc32, C.c_void_p).value
    n = nat.inflate_task(mv.ctypes.data, len(img), chain.ctypes.data, len(chain), ss, sa.ctypes.data, 3, out.ctypes.data, len(out), sizes.ctypes.data,
                         tmp.ctypes.data, len(tmp), dec, fnp, crcp, bad.ctypes.data)
    assert n == 3 * (8 + 3000) and bad.tolist() == [0, 1, 0], (n, bad.tolist())
    assert bytes(out[8:8 + 3000]) == pays[0]
    del mv


def test_unknown_channel_values_keep_every_segment():
    """segments without a channel (3-tuples, e.g. a channel value outside 101/102/103) form one group in stream order; with channels, one group each"""
    segs3 = [(100 * i, 50, 1000) for i in range(6)]
    assert Q._chan_groups(segs3) == [list(range(6))]
    assert len(Q.plan(0, 'p', segs3, task_mb=0.003, ovl=1)) >= 1
    segs4 = [(0, 50, 10, 101), (50, 50, 10, 102), (100, 50, 10, 103), (150, 50, 10, 101), (200, 50, 10, 102)]
    assert Q._chan_groups(segs4) == [[0, 3], [1, 4], [2]]


def test_two_files_in_one_process_do_not_share_native_cache():
    """regression: _native() cached the mmap/chains/ids of the first file per process; a second query (other file) read stale data and hung/decoded wrong.
    Needs the corpus and _rvtframe.so (skipped otherwise)."""
    import glob, json
    so = os.path.join(HERE, 'rvtballet', '_rvtframe.so'); fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/20*/*.rvt')))[:1] + sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*.rvt')))[:1]
    if not os.path.exists(so) or len(fs) < 2: pytest.skip('no .so / corpus')
    a = [json.dumps(Q.sheets(f, workers=2), sort_keys=True, default=str) for f in fs + fs[:1]]
    Q.NATIVE = False
    try: b = [json.dumps(Q.sheets(f, workers=2), sort_keys=True, default=str) for f in fs + fs[:1]]
    finally: Q.NATIVE = True
    assert a == b


def test_cpu_gate_blocks_native_on_old_cpu(monkeypatch):
    from rvtballet import fastquery as fq
    monkeypatch.setenv("RVT_Q_CPUFLAGS", "sse2 avx")             # no avx2/bmi2: the v3 .so must not be loaded (SIGILL)
    assert fq._cpu_v3() is False
    monkeypatch.setenv("RVT_Q_CPUFLAGS", "avx2 bmi1 bmi2 fma movbe abm")
    assert fq._cpu_v3() is True


@pytest.mark.parametrize("sample", ["2020/22_rme_basic_sample_project.rvt", "2024/42_Snowdon_Towers_Sample_HVAC.rvt"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_damaged_real_sample_native_equals_python(sample, seed, tmp_path):
    """real Autodesk sample (skipped when absent), 8 bit flips in one 4 KB window: the native path must give the same stdout and exit code as RVT_Q_NATIVE=0 and never die on a signal (CRC retry / fallback)"""
    import subprocess
    src = os.path.join(os.path.expanduser("~/rvt-research/corpus"), sample)
    if not os.path.exists(src): pytest.skip("sample absent")
    b = bytearray(open(src, "rb").read()); rnd = random.Random(seed); o = rnd.randrange(len(b) // 4, len(b) - 4096)
    for _ in range(8): b[o + rnd.randrange(4096)] ^= 1 << rnd.randrange(8)
    f = str(tmp_path / "x.rvt"); open(f, "wb").write(b)
    r = {}
    for n in ("1", "0"):
        p = subprocess.run([sys.executable, "-m", "rvtballet.fastquery", "walls", f, "--json"], cwd=HERE, capture_output=True, timeout=300, env=dict(os.environ, RVT_Q_NATIVE=n))
        assert p.returncode >= 0, "died on signal %d (native=%s)" % (-p.returncode, n)
        r[n] = (p.returncode, p.stdout)
    assert r["1"] == r["0"]


@pytest.mark.parametrize("cmd", ["doors", "counts"])
def test_header_window_split_same_answer(cmd):
    """RVT_Q_HDR_MAXWIN=4 (split long merged header windows into parallel jobs) must answer exactly like 0 (old merge-everything)"""
    import subprocess, hashlib
    src = os.path.join(os.path.expanduser("~/rvt-research/corpus"), "2024/42_Snowdon_Towers_Sample_HVAC.rvt")
    if not os.path.exists(src): pytest.skip("sample absent")
    h = {}
    for w in ("0", "4"):
        p = subprocess.run([sys.executable, "-m", "rvtballet.fastquery", cmd, src, "--json"], cwd=HERE, capture_output=True, timeout=300, env=dict(os.environ, RVT_Q_HDR_MAXWIN=w))
        assert p.returncode == 0; h[w] = hashlib.sha1(p.stdout).hexdigest()
    assert h["0"] == h["4"]


def test_header_window_split_default_is_off():
    """RVT_Q_HDR_MAXWIN>0 gave non-deterministic wall-types (category lost in about half of the cold runs, 19_Commercial and 27_Technical_school samples); the default must stay 0 until that is understood. test_header_window_split_same_answer does not cover wall-types"""
    assert Q.HDR_MAXWIN == 0


@pytest.mark.parametrize("sample", ["2021/27_Technical_school-current_m.rvt", "2022/33_Technical_school-current_m.rvt"])
def test_wall_types_always_have_category_walls_family(sample):
    """2021/2022 Technical_school: the ElementHeader of wall types 399/403/411 carries category -1 (the 2024 file has Walls); wall-types used to print category null for them. Every WallType has a category (Walls or Stacked Walls)"""
    import subprocess, json
    src = os.path.join(os.path.expanduser("~/rvt-research/corpus"), sample)
    if not os.path.exists(src): pytest.skip("sample absent")
    p = subprocess.run([sys.executable, "-m", "rvtballet.fastquery", "wall-types", src, "--json"], cwd=HERE, capture_output=True, timeout=300)
    assert p.returncode == 0
    d = json.loads(p.stdout); assert len(d) == 32
    assert [x["id"] for x in d if x["category"] is None] == []
    assert {x["id"]: x["category"] for x in d}[399] == "Walls"


def test_weak_candidate_needs_a_plausible_id():
    """an uncheckable candidate (record past the chunk end) forces the old scan only when its id is plausible (2025/2026 files have many more schema tags, so random
    bytes gave false weak candidates and half the tasks fell back); same rule in rvtframe.c and frame_records"""
    r, L = rec(500, 20, bytes(20)); real = bytes(8) + struct.pack('<I', 0) + r[:-10]
    assert frame(real) is None
    r2, _ = rec((1 << 31) if W == 4 else (1 << 50), 20, bytes(20)); junk = bytes(8) + struct.pack('<I', 0) + r2[:-10]
    assert frame(junk) == []


def test_es_schemas_independent_of_es_thread_count():
    """the ES child (RVT_Q_ES_THREADS) must not change what the schema search finds: sheets output of a Snowdon MEP sample (4-5 MB Global/Latest, the slow case) is
    byte-identical for 1 and 4 threads (also holds for the old single-threaded rvt_core)"""
    import glob, subprocess, sys
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/4[25]_Snowdon*.rvt')))
    if not fs: pytest.skip('public corpus missing')
    outs = []
    for th in ('1', '4'):
        r = subprocess.run([sys.executable, '-m', 'rvtballet.fastquery', 'sheets', fs[0]], cwd=HERE, env=dict(os.environ, RVT_Q_ES_THREADS=th), capture_output=True, text=True, timeout=300)
        assert r.returncode == 0 and 'Sheets' in r.stdout; outs.append(r.stdout)
    assert outs[0] == outs[1]
