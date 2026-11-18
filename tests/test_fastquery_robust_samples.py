"""fastquery robustness on a PUBLIC Autodesk sample (skipped when the corpus is absent): unknown channel word -> old walk (same output), a flipped byte in a
102 segment -> CRC WARNING while one in a 103 segment is never read, a file replaced between two queries in one process -> fresh answer."""
import glob, os, shutil, struct, subprocess, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fs = sorted(glob.glob(os.path.expanduser("~/rvt-research/corpus/2024/*.rvt")), key=os.path.getsize)
pytestmark = pytest.mark.skipif(len(_fs) < 2, reason="public corpus missing")
GZ = b"\x1f\x8b\x08\x00"


def q(path, cmd="walls", **env):
    e = dict(os.environ, **env)
    r = subprocess.run([sys.executable, "-m", "rvtballet.fastquery", cmd, path, "--verbose"], cwd=ROOT, env=e, capture_output=True, text=True, timeout=300)
    return r.stdout, r.stderr


def segs(d, ch):
    pos = 0
    while True:
        i = d.find(GZ, pos)
        if i < 0: return
        pos = i + 1
        if i >= 24:
            w = struct.unpack_from("<6I", d, i - 24)
            if w[4] == ch and 34 <= w[2] <= len(d) and w[0] < 16 and w[3] > 0: yield i, w[2]


@pytest.mark.parametrize("val", [100, 104, 0, 0xFFFFFFFF])
def test_unknown_channel_word_same_output(tmp_path, val):
    d = bytearray(open(_fs[0], "rb").read()); ref = q(_fs[0])[0]
    i = list(segs(d, 102))[3][0]; struct.pack_into("<I", d, i - 24 + 16, val)
    p = tmp_path / "u.rvt"; p.write_bytes(d)
    assert q(str(p))[0] == ref


def test_crc_flip_102_warns_103_silent(tmp_path):
    d0 = open(_fs[0], "rb").read(); ref = q(_fs[0])[0]
    for ch, warn in ((103, False), (102, True)):
        d = bytearray(d0); i, L = list(segs(d, ch))[3]; d[i + 10 + L // 2 - 10] ^= 0xFF
        p = tmp_path / ("c%d.rvt" % ch); p.write_bytes(d)
        out, err = q(str(p))
        assert ("fail their CRC" in err) == warn
        if not warn: assert out == ref


def test_replace_between_queries_is_fresh(tmp_path):
    from rvtballet import fastquery as fq
    p = str(tmp_path / "x.rvt"); shutil.copyfile(_fs[0], p); a = repr(fq.collect(p, category="Walls"))
    shutil.copyfile(_fs[1], str(tmp_path / "y.rvt")); os.replace(str(tmp_path / "y.rvt"), p)
    assert repr(fq.collect(p, category="Walls")) == repr(fq.collect(_fs[1], category="Walls"))
