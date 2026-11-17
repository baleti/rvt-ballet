"""elemindex regression tests (Autodesk sample only; skipped when the sample is absent). Run: RVT_SAMPLE=/path/to/18_rst_basic_sample_project.rvt pytest tests/test_elemindex.py"""
import os, sys, shutil, tempfile, random
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import elemindex as X

SAMPLE = os.environ.get("RVT_SAMPLE", os.path.expanduser("~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt"))
pytestmark = pytest.mark.skipif(not os.path.exists(SAMPLE), reason="Autodesk sample not available")


@pytest.fixture(scope="module")
def work():
    d = tempfile.mkdtemp(prefix="elemindex-test-"); p = os.path.join(d, "s.rvt"); shutil.copyfile(SAMPLE, p)
    X.CACHE = os.path.join(d, "cache")
    yield p
    shutil.rmtree(d, ignore_errors=True)


def test_segment_chain_matches_marker_scan(work):
    X._paths(); import rvt2text as T
    o = X._open(work); n = [e for e in ("/".join(x) for x in o.listdir(streams=True)) if e.startswith("Partitions/")][0]
    assert len(X.Part(o, n).segments()) == sum(1 for _ in T.segments(o.openstream(n).read()))


def test_verify_partition_clean(work):
    o = X._open(work)
    for e in o.listdir(streams=True):
        n = "/".join(e)
        if n.startswith("Partitions/"):
            r = X.verify_partition(o, n); assert r["bad"] == [] and r["covered"]


def test_index_lookup_decodes_complete_record(work):
    idx = X.build(work, workers=2); rd = X.Reader(work, idx)
    rows = [j for j in range(len(idx["id"])) if int(idx["off"][j]) >= 0]; random.seed(1)
    ok = 0; sample = random.sample(rows, 60)
    for j in sample:
        g = rd.get(int(idx["id"][j]))
        if g and g["record"]: ok += 1
    assert ok >= 0.95 * len(sample)


def test_cache_key_changes_on_inplace_edit_with_restored_mtime(work):
    k0 = X.key(work); st = os.stat(work)
    with open(work, "r+b") as f: f.seek(2_000_000); b = f.read(1); f.seek(2_000_000); f.write(bytes([b[0] ^ 1]))
    os.utime(work, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert os.stat(work).st_size == st.st_size and X.key(work) != k0
    with pytest.raises(FileNotFoundError): X.load(work)       # the stale index is not served


def test_compare_partitions_identical_ok_and_interlude_flip_detected(work):
    # work fixture file was modified by the key test above; use a fresh copy
    d = tempfile.mkdtemp(prefix="elemindex-cmp-"); a = os.path.join(d, "a.rvt"); b = os.path.join(d, "b.rvt"); shutil.copyfile(SAMPLE, a); shutil.copyfile(SAMPLE, b)
    try:
        oa = X._open(a); n = [e for e in ("/".join(x) for x in oa.listdir(streams=True)) if e.startswith("Partitions/")][0]
        assert X.compare_partitions(oa, X._open(b), n)["ok"]
        P = X.Part(oa, n); segs = P.segments(); gaps = X._gaps(P, segs); first = min(i for i in gaps if 0 < i < len(segs))
        pos = segs[first][0] - 24 - 1                                  # last byte of the interlude before segment `first`, payload offset -> stored offset
        pg, po = divmod(pos, X.PAGE_PAYLOAD); stored = pg * X.PAGE_STORED + po
        ent = oa.direntries[oa._find(n)]; ss = oa.sectorsize; k = stored // ss
        # locate the byte through the sector chain of the stream in file b
        ob = X._open(b); Pb = X.Part(ob, n); fo = (Pb.chain[k] + 1) * ss + stored % ss
        with open(b, "r+b") as f: f.seek(fo); c = f.read(1); f.seek(fo); f.write(bytes([c[0] ^ 0xFF]))
        r = X.compare_partitions(X._open(a), X._open(b), n)
        assert not r["ok"] and any("interlude" in x for x in r["reasons"])
    finally: shutil.rmtree(d, ignore_errors=True)


def _flip_payload_byte(path, name, pos, mask=0xFF):
    ob = X._open(path); P = X.Part(ob, name); pg, po = divmod(pos, X.PAGE_PAYLOAD); st = pg * X.PAGE_STORED + po; ss = ob.sectorsize
    fo = (P.chain[st // ss] + 1) * ss + st % ss
    with open(path, "r+b") as f: f.seek(fo); c = f.read(1); f.seek(fo); f.write(bytes([c[0] ^ mask]))


@pytest.mark.parametrize("mutation", ["segment_data", "gzip_crc", "interlude", "head_count_only", "head_marker", "footer_len", "footer_tag", "first_bytes_after_header", "gzip_mtime", "gzip_os", "hdr_kind", "hdr_w5", "hdr_w3"])
def test_gate_catches_corruption(mutation):
    """ESCAPE hunt: each single-spot corruption of a copy must fail compare_partitions (hard reason), the untouched copy must pass"""
    d = tempfile.mkdtemp(prefix="elemindex-esc-"); a = os.path.join(d, "a.rvt"); b = os.path.join(d, "b.rvt"); shutil.copyfile(SAMPLE, a); shutil.copyfile(SAMPLE, b)
    try:
        oa = X._open(a); n = [e for e in ("/".join(x) for x in oa.listdir(streams=True)) if e.startswith("Partitions/")][0]
        P = X.Part(oa, n); segs = P.segments(); gaps = X._gaps(P, segs); mid = len(segs) // 2
        off, ln, il = segs[mid]
        if mutation == "segment_data": _flip_payload_byte(b, n, off + ln // 2)                  # inside the deflate stream
        elif mutation == "gzip_crc": _flip_payload_byte(b, n, off + ln - 16)                     # CRC32 of the member
        elif mutation == "footer_len": _flip_payload_byte(b, n, off + ln - 6)                    # u32 stored_len copy in the 8-byte segment footer
        elif mutation == "footer_tag": _flip_payload_byte(b, n, off + ln - 8)
        elif mutation == "first_bytes_after_header": _flip_payload_byte(b, n, off + 3)         # gzip header MTIME byte (not covered by the CRC)
        elif mutation == "gzip_mtime": _flip_payload_byte(b, n, off + 5)
        elif mutation == "hdr_kind": _flip_payload_byte(b, n, off - 24, 0x08)
        elif mutation == "hdr_w5": _flip_payload_byte(b, n, off - 24 + 20, 0x01)
        elif mutation == "hdr_w3": _flip_payload_byte(b, n, off - 24 + 12, 0x01)
        elif mutation == "gzip_os": _flip_payload_byte(b, n, off + 9)
        elif mutation == "interlude": _flip_payload_byte(b, n, segs[min(i for i in gaps if 0 < i < len(segs))][0] - 24 - 1)
        elif mutation == "head_count_only": _flip_payload_byte(b, n, 14, 0x01)                   # element count of the partition head without touching ElemTable
        elif mutation == "head_marker": _flip_payload_byte(b, n, 0, 0x01)
        r = X.compare_partitions(oa, X._open(b), n)
        assert not r["ok"], (mutation, r)
    finally: shutil.rmtree(d, ignore_errors=True)


def test_gate_rejects_zeroed_trailer():
    """Revit 2024 refuses a file whose partition trailer run is zeroed (CorruptModelException, VM-judged 2026-11-14); compare_partitions must hard-fail it, while a 1-bit flip (opens clean) stays a warning"""
    orig = os.path.expanduser("~/demo-state/c3x-codexlab-oracle/2024_hvac_original.rvt"); z = os.path.expanduser("~/c9x-var24/tail_zero.rvt"); fl = os.path.expanduser("~/c9x-var24/tail_flip1.rvt")
    if not all(os.path.exists(p) for p in (orig, z, fl)): pytest.skip("trailer variants not available")
    X._paths(); a = X._open(orig)
    assert not X.compare_partitions(a, X._open(z), "Partitions/21")["ok"]
    assert X.compare_partitions(a, X._open(fl), "Partitions/21")["ok"]


def test_last_page_ecc_check():
    """the trailer block is the last page's ECC parity: a legit writer output verifies, the VM-refused zeroed variant does not (a 1-bit flip also fails here: stricter than Revit, which corrects it)"""
    orig = os.path.expanduser("~/demo-state/c3x-codexlab-oracle/2024_hvac_original.rvt"); z = os.path.expanduser("~/c9x-var24/tail_zero.rvt")
    if not all(os.path.exists(p) for p in (orig, z)): pytest.skip("variants not available")
    X._paths()
    assert X._last_page_ecc_ok(X._open(orig), "Partitions/21") is True
    assert X._last_page_ecc_ok(X._open(z), "Partitions/21") is False
