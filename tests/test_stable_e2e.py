"""end to end: the real `rvt-ballet levels` command against an Autodesk sample copy that is rewritten while the command runs (each write pattern).
Acceptable: the exact reference answer (file not touched yet / finished before) or exit 75/1 with a message. A different answer with exit 0 = torn read."""
import os, sys, subprocess, shutil, tempfile, threading, time, random, pytest
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk sample not available')
ROOT = os.path.join(os.path.dirname(__file__), '..')


def run(f, *extra):
    p = subprocess.run([sys.executable, '-m', 'rvtballet', 'levels', f, '--quiet-secs', '0'] + list(extra), cwd=ROOT, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


def junk_inplace(f, delay):
    time.sleep(delay); sz = os.path.getsize(f); r = random.Random(5)
    with open(f, 'r+b') as o:
        for _ in range(40): o.seek(r.randrange(0, sz - 4096)); o.write(r.randbytes(4096)); o.flush(); time.sleep(0.01)
def trunc_rewrite(f, delay):
    time.sleep(delay); b = open(SRC, 'rb').read()
    with open(f, 'wb') as o:
        for i in range(0, len(b), 1 << 20): o.write(b[i:i + (1 << 20)]); o.flush(); time.sleep(0.01)
def temp_rename(f, delay):
    time.sleep(delay); shutil.copyfile(SRC, f + '.tmp'); os.replace(f + '.tmp', f)
def append_tail(f, delay):
    time.sleep(delay)
    with open(f, 'ab') as o: o.write(b'\0' * (1 << 20)); o.flush()


@pytest.fixture(scope='module')
def ref():
    d = tempfile.mkdtemp(prefix='stable-e2e-'); f = os.path.join(d, 'a.rvt'); shutil.copyfile(SRC, f); t = time.time() - 100; os.utime(f, (t, t))
    rc, out, err = run(f); assert rc == 0, err
    yield d, out; shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize('w', [junk_inplace, trunc_rewrite, temp_rename, append_tail], ids=lambda w: w.__name__)
@pytest.mark.parametrize('delay', [0.0, 0.5, 1.5])
def test_levels_during_rewrite(ref, w, delay):
    d, good = ref; f = os.path.join(d, 'b.rvt'); shutil.copyfile(SRC, f); t = time.time() - 100; os.utime(f, (t, t))
    th = threading.Thread(target=w, args=(f, delay)); th.start(); rc, out, err = run(f); th.join()
    assert (rc == 0 and out == good) or rc in (75, 1), 'torn read: rc=%s out=%r err=%r' % (rc, out[:200], err[:200])


def test_quiet_period_refuses_fresh_file(ref):
    d, good = ref; f = os.path.join(d, 'c.rvt'); shutil.copyfile(SRC, f)           # mtime = now
    p = subprocess.run([sys.executable, '-m', 'rvtballet', 'levels', f, '--quiet-secs', '3'], cwd=ROOT, capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, RVTBALLET_X='1'))
    assert p.returncode == 0 and p.stdout == good                                  # waited and answered after the quiet period (retries cover 3 s)


def test_snapshot_option(ref):
    d, good = ref; rc, out, err = run(os.path.join(d, 'a.rvt'), '--snapshot'); assert rc == 0 and out == good
    assert not [x for x in os.listdir(tempfile.gettempdir()) if x.startswith('rvtsnap-') and os.path.isdir(os.path.join(tempfile.gettempdir(), x)) and os.listdir(os.path.join(tempfile.gettempdir(), x))]


@pytest.mark.parametrize('kind', ['touch', 'rewrite_same_bytes', 'rename_same_bytes'])
def test_continuous_writer_always_refused(ref, kind):
    """a save that keeps going for the whole query (same content, new mtime / new inode every 50 ms): the answer must be refused every time"""
    d, good = ref; f = os.path.join(d, 'k.rvt'); shutil.copyfile(SRC, f); stop = threading.Event(); data = open(SRC, 'rb').read(8 << 20)
    def w():
        while not stop.is_set():
            if kind == 'touch': os.utime(f, None)
            elif kind == 'rewrite_same_bytes':
                with open(f, 'r+b') as o: o.write(data[:4096])
            else: shutil.copyfile(SRC, f + '.n'); os.replace(f + '.n', f)
            time.sleep(0.05)
    th = threading.Thread(target=w); th.start()
    try: rc, out, err = run(f)
    finally: stop.set(); th.join()
    assert rc == 75 and not out.strip(), 'rc=%s out=%r err=%r' % (rc, out[:100], err[:200])


def test_snapshot_under_continuous_writer_refuses_and_cleans(ref, tmp_path):
    """--snapshot while the source keeps changing: no answer (exit 75), and no private copy left in the temp dir"""
    d, good = ref; f = os.path.join(d, 's.rvt'); shutil.copyfile(SRC, f); stop = threading.Event()
    before = {n for n in os.listdir(tempfile.gettempdir()) if n.startswith('rvtsnap-')}
    def w():
        while not stop.is_set(): os.utime(f, None); time.sleep(0.02)
    th = threading.Thread(target=w); th.start()
    try: rc, out, err = run(f, '--snapshot')
    finally: stop.set(); th.join()
    assert rc == 75 and not out.strip(), 'rc=%s out=%r err=%r' % (rc, out[:100], err[:200])
    left = [n for n in os.listdir(tempfile.gettempdir()) if n.startswith('rvtsnap-') and n not in before]
    assert not left, left
