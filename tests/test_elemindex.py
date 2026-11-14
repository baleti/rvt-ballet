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
        P = X.Part(oa, n); segs = P.segments(); gaps = X._gaps(P, segs); first = min(i for i in gaps if i < len(segs))
        pos = segs[first][0] - 24 - 1                                  # last byte of the interlude before segment `first`, payload offset -> stored offset
        pg, po = divmod(pos, X.PAGE_PAYLOAD); stored = pg * X.PAGE_STORED + po
        ent = oa.direntries[oa._find(n)]; ss = oa.sectorsize; k = stored // ss
        # locate the byte through the sector chain of the stream in file b
        ob = X._open(b); Pb = X.Part(ob, n); fo = (Pb.chain[k] + 1) * ss + stored % ss
        with open(b, "r+b") as f: f.seek(fo); c = f.read(1); f.seek(fo); f.write(bytes([c[0] ^ 0xFF]))
        r = X.compare_partitions(X._open(a), X._open(b), n)
        assert not r["ok"] and any("interlude" in x for x in r["reasons"])
    finally: shutil.rmtree(d, ignore_errors=True)
