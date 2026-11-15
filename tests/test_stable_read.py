"""torn-read guard (rvtballet/stable.py): every observed or plausible way an application rewrites a .rvt while a reader is working must end in
FileChanged / InUse / Damaged, never in a silently wrong answer. Synthetic data only (random bytes + a hand-built compound file)."""
import os, struct, threading, time, random, tempfile, shutil, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet import stable as S

SIZE = 3 << 20


def blob(seed, n=SIZE): return random.Random(seed).randbytes(n)


@pytest.fixture
def d():
    p = tempfile.mkdtemp(prefix='stabletest-'); yield p; shutil.rmtree(p, ignore_errors=True)


def mk(d, name='m.rvt', seed=1, n=SIZE, age=100):
    f = os.path.join(d, name); open(f, 'wb').write(blob(seed, n)); t = time.time() - age; os.utime(f, (t, t)); return f


def reader(f, delay=0.0, holder=None):
    """a 'query': reads the whole file in 64 KB steps, returns its checksum (stands for any answer derived from the bytes)"""
    import zlib; c = 0
    with open(f, 'rb') as a:
        while True:
            b = a.read(65536)
            if not b: break
            c = zlib.crc32(b, c)
            if delay: time.sleep(delay)
    return c


# ---- write patterns (each runs in a thread while the reader is in the middle of the read) ----
def w_inplace(f, new):
    with open(f, 'r+b') as o:
        for i in range(0, len(new), 65536): o.seek(i); o.write(new[i:i + 65536]); o.flush(); time.sleep(0.002)
def w_inplace_keep_mtime(f, new):
    st = os.stat(f); w_inplace(f, new); os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
def w_truncate_rewrite(f, new):
    with open(f, 'wb') as o:
        for i in range(0, len(new), 65536): o.write(new[i:i + 65536]); o.flush(); time.sleep(0.002)
def w_temp_rename(f, new):
    t = f + '.tmp'; open(t, 'wb').write(new); os.replace(t, f)
def w_append(f, new):
    with open(f, 'ab') as o:
        for i in range(0, 1 << 20, 65536): o.write(new[i:i + 65536]); o.flush(); time.sleep(0.002)
def w_replace_symlink(f, new):
    t = f + '.new'; open(t, 'wb').write(new); os.remove(f); os.symlink(t, f)

PATTERNS = [w_inplace, w_inplace_keep_mtime, w_truncate_rewrite, w_temp_rename, w_append, w_replace_symlink]


@pytest.mark.parametrize('pat', PATTERNS, ids=lambda p: p.__name__)
def test_guard_never_silently_wrong(d, pat):
    f = mk(d); old = reader(f); new = blob(2)
    outcome = None
    try:
        with S.guard(f, quiet=0, retries=0, check=False):
            th = threading.Thread(target=pat, args=(f, new)); th.start()
            ans = reader(f, delay=0.001); th.join()
    except S.FileChanged: outcome = 'changed'
    else: outcome = 'answer'
    assert outcome == 'changed', '%s: the reader got an answer (%s) from a file rewritten under it' % (pat.__name__, ans == old)


def test_guard_unchanged_ok(d):
    f = mk(d)
    with S.guard(f, quiet=0, retries=0, check=False) as g: a = reader(f)
    assert a == reader(f) and g.fingerprint[0] == SIZE


def test_error_inside_block_blamed_on_change(d):
    f = mk(d)
    with pytest.raises(S.FileChanged):
        with S.guard(f, quiet=0, retries=0, check=False):
            w_truncate_rewrite(f, blob(3, 1000)); raise ValueError('parse error caused by a torn read')


def test_error_inside_block_unchanged_file_propagates(d):
    f = mk(d)
    with pytest.raises(ValueError):
        with S.guard(f, quiet=0, retries=0, check=False): raise ValueError('genuine bug')


def test_same_size_same_mtime_overwrite_caught_by_samples(d):
    f = mk(d); fp0 = S.fingerprint(f); st = os.stat(f)
    with open(f, 'r+b') as o: o.seek(0); o.write(b'X' * 100)                  # head block
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert 'sampled content' in fp0.diff(S.fingerprint(f))


def test_tail_overwrite_caught(d):
    f = mk(d); fp0 = S.fingerprint(f); st = os.stat(f)
    with open(f, 'r+b') as o: o.seek(SIZE - 10); o.write(b'Y' * 10)
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert S.fingerprint(f).diff(fp0)


def test_zero_length_and_missing(d):
    f = os.path.join(d, 'z.rvt'); open(f, 'wb').close()
    with pytest.raises(S.Damaged): S.cfb_check(f)
    with pytest.raises(S.InUse): S.wait_quiet(os.path.join(d, 'nope.rvt'), quiet=0, retries=0)


def test_unreadable_file(d):
    if os.geteuid() == 0: pytest.skip('root ignores modes')
    f = mk(d); os.chmod(f, 0)
    with pytest.raises(OSError): S.fingerprint(f)


def test_quiet_period_waits_then_succeeds(d):
    f = mk(d, age=0); slept = []
    def fake_sleep(x): slept.append(x); t = time.time() - 100; os.utime(f, (t, t))   # the writer finished while we waited
    S.wait_quiet(f, quiet=5, retries=3, backoff=0.01, sleep=fake_sleep)
    assert slept


def test_quiet_period_gives_up(d):
    f = mk(d, age=0)
    with pytest.raises(S.InUse) as e: S.wait_quiet(f, quiet=60, retries=2, backoff=0.001)
    assert 'modified' in str(e.value)


def test_moving_stat_detected(d):
    f = mk(d); st = {'n': 0}
    def sl(x): st['n'] += 1; open(f, 'ab').write(b'1')       # grows while we settle
    with pytest.raises(S.InUse): S.wait_quiet(f, quiet=0, retries=1, settle=0.01, sleep=sl, backoff=0)


def test_fresh_side_file_blocks(d):
    f = mk(d); open(os.path.join(d, 'm.0001.rvt'), 'wb').write(b'x'); open(os.path.join(d, 'm.rvt.tmp'), 'wb').write(b'x')
    assert S.side_files(f) == ['m.0001.rvt', 'm.rvt.tmp']
    with pytest.raises(S.InUse): S.wait_quiet(f, quiet=5, retries=0, settle=0)
    assert S.side_files(f, within=0.0, now=time.time() + 100) == []         # old side files do not block


def test_unrelated_neighbour_ignored(d):
    f = mk(d); open(os.path.join(d, 'other.rvt'), 'wb').write(b'x')
    assert S.side_files(f) == []


def test_disabled_by_env(d, monkeypatch):
    monkeypatch.setenv(S.ENV_OFF, '1'); f = mk(d, age=0)
    with S.guard(f) as g: assert g is None


# ---- compound file structure check ----
def mini_cfb(nsect=8, ss=512):
    """a header + FAT with `nsect` data sectors all marked in use; valid enough for cfb_check"""
    h = bytearray(512); h[:8] = bytes.fromhex('D0CF11E0A1B11AE1'); struct.pack_into('<H', h, 30, 9)
    struct.pack_into('<I', h, 44, 1); struct.pack_into('<II', h, 68, 0xFFFFFFFE, 0)
    ent = [0xFFFFFFFF] * 109; ent[0] = 0; struct.pack_into('<109I', h, 76, *ent)
    fat = [0xFFFFFFFD] + [i + 2 for i in range(nsect - 1)] + [0xFFFFFFFE] + [0xFFFFFFFF] * (128 - 1 - nsect)
    return bytes(h) + struct.pack('<128I', *fat) + bytes(512 * nsect)


def test_cfb_ok_and_truncated(d):
    f = os.path.join(d, 'c.rvt'); b = mini_cfb(); open(f, 'wb').write(b); S.cfb_check(f)
    for cut in (len(b) - 1, len(b) - 512, 700, 100, 0):
        open(f, 'wb').write(b[:cut])
        with pytest.raises(S.Damaged): S.cfb_check(f)


def test_cfb_bad_signature(d):
    f = os.path.join(d, 'c.rvt'); open(f, 'wb').write(b'PK' + bytes(2000))
    with pytest.raises(S.Damaged): S.cfb_check(f)


# ---- snapshot ----
def test_snapshot_copies_and_cleans(d):
    f = os.path.join(d, 's.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t)); seen = {}
    with S.snapshot(f, tmpdir=d, quiet=0) as c:
        seen['c'] = c; assert open(c, 'rb').read() == open(f, 'rb').read() and c != f
    assert not os.path.exists(seen['c']) and not os.path.isdir(os.path.dirname(seen['c']))


def test_snapshot_retries_when_source_changes(d):
    f = os.path.join(d, 's.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t)); n = {'i': 0}
    orig = S.fingerprint
    def flaky(path, fd=None):
        r = orig(path, fd)
        if path == f:
            n['i'] += 1
            if n['i'] == 2:                                         # 'after the copy' fingerprint of attempt 1: pretend it moved
                return S.Fingerprint((r[0], r[1] + 1, r[2], r[3], r[4]))
        return r
    S.fingerprint = flaky
    try:
        with S.snapshot(f, tmpdir=d, quiet=0, attempts=3) as c: assert os.path.exists(c)
    finally: S.fingerprint = orig
    assert n['i'] == 4      # two attempts: (before, after) each


def test_snapshot_gives_up(d):
    f = os.path.join(d, 's.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t)); orig = S.fingerprint; k = {'i': 0}
    def always(path, fd=None):
        r = orig(path, fd); k['i'] += 1
        return S.Fingerprint((r[0], r[1] + k['i'], r[2], r[3], r[4])) if path == f else r
    S.fingerprint = always
    try:
        with pytest.raises(S.InUse):
            with S.snapshot(f, tmpdir=d, quiet=0, attempts=2): pass
    finally: S.fingerprint = orig
    assert [x for x in os.listdir(d) if x.startswith('rvtsnap-')] == []


def test_snapshot_no_space(d, monkeypatch):
    f = os.path.join(d, 's.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t))
    monkeypatch.setattr(S, '_free', lambda p: 0)
    with pytest.raises(OSError):
        with S.snapshot(f, tmpdir=d, quiet=0): pass


def test_fuzz_timing(d):
    """random write start delays against a running reader, many rounds: an answer is only acceptable when it equals the old content"""
    rnd = random.Random(7); bad = 0; changed = 0
    for i in range(25):
        f = mk(d, name='f%d.rvt' % i, seed=i); old = reader(f); pat = rnd.choice(PATTERNS[:5]); new = blob(100 + i)
        try:
            with S.guard(f, quiet=0, retries=0, check=False):
                def late(): time.sleep(rnd.random() * 0.05); pat(f, new)
                th = threading.Thread(target=late); th.start(); ans = reader(f, delay=0.001); th.join()
            if ans != old: bad += 1                                           # accepted a mixed answer
        except S.FileChanged: changed += 1
    assert bad == 0 and changed > 0


def test_future_mtime_clock_skew_does_not_block_forever(d):
    """a share whose clock runs ahead (mtime an hour in the future) must not be refused for ever: the age is meaningless, the settle check decides"""
    f = mk(d); t = time.time() + 3600; os.utime(f, (t, t))
    S.wait_quiet(f, quiet=5, retries=0, settle=0.01)
    with S.guard(f, quiet=5, check=False): pass


def test_small_future_skew_waits_like_recent(d):
    f = mk(d); t = time.time() + 2; os.utime(f, (t, t))        # 2 s ahead: still looks freshly written
    with pytest.raises(S.InUse): S.wait_quiet(f, quiet=5, retries=0, settle=0)


def test_run_file_deleted_during_read(d, capsys):
    f = os.path.join(d, 'm.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t)); os.environ[S.ENV_QUIET] = '0'
    try:
        S._ACTIVE.clear(); rc = S.run([f, '--quiet-secs', '0'], lambda a, s: (os.remove(f), 0)[1])
    finally: os.environ.pop(S.ENV_QUIET, None)
    assert rc == 75 and 'changed' in capsys.readouterr().err


def test_run_snapshot_source_vanishes(d, capsys, monkeypatch):
    f = os.path.join(d, 'm.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t))
    real = open
    import builtins
    def bad_open(p, *a, **k):
        if p == f: os.remove(f)
        return real(p, *a, **k)
    monkeypatch.setattr(builtins, 'open', bad_open)
    rc = S.run([f, '--snapshot', '--quiet-secs', '0'], lambda a, s: 0)
    assert rc in (75, 1) and 'Traceback' not in capsys.readouterr().err


def test_run_bad_quiet_arg(d):
    assert S.run(['x.rvt', '--quiet-secs', 'abc'], lambda a, s: 0) == 2


def test_full_hash_catches_write_between_samples(d, monkeypatch):
    f = os.path.join(d, 'big.bin'); n = S.HEAD + 2 * S.BLOCK * S.NSAMPLES + (4 << 20)
    open(f, 'wb').write(b'\0' * n)
    offs = S._offsets(n); gap = None
    for o in range(S.HEAD, n - S.HEAD):
        if all(not (a <= o < a + l) for a, l in offs): gap = o; break
    assert gap is not None
    def edit():
        st = os.stat(f)
        with open(f, 'r+b') as o: o.seek(gap); o.write(b'X')
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    a = S.fingerprint(f); edit(); b = S.fingerprint(f)
    assert not a.diff(b)  # sampled mode misses it: documented residual risk
    monkeypatch.setenv(S.ENV_FULL, '1')
    f2 = os.path.join(d, 'big2.bin'); open(f2, 'wb').write(b'\0' * n)
    a = S.fingerprint(f2); st = os.stat(f2)
    with open(f2, 'r+b') as o: o.seek(gap); o.write(b'X')
    os.utime(f2, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert 'sampled content' in a.diff(S.fingerprint(f2))


def test_info_save_is_guarded(d, monkeypatch, capsys):
    from rvtballet import cli, editcli
    f = os.path.join(d, 'm.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t))
    seen = []
    def fake(argv, say=print):
        seen.append(argv); st = os.stat(f); os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9)); return 0
    monkeypatch.setattr(editcli, 'info_main', fake)
    with pytest.raises(SystemExit) as e: cli.main(['info', '--save', f, '--quiet-secs', '0'])
    assert seen and e.value.code == 75 and 'changed' in capsys.readouterr().err


def test_savegate_temp_is_a_side_file(d):
    f = mk(d); name = os.path.basename(f)
    open(os.path.join(d, '.%s.3d8c73.a7273n40.sgtmp' % name), 'wb').write(b'x')
    assert S.side_files(f) == ['.%s.3d8c73.a7273n40.sgtmp' % name]


def test_revit_backup_folder_touched_is_a_side_file(d):
    f = mk(d); stem = os.path.splitext(os.path.basename(f))[0]
    os.mkdir(os.path.join(d, stem + '_backup'))      # Revit writes <name>_backup\\<name>.000N.rvt next to the model on every save
    assert S.side_files(f) == [stem + '_backup']
    old = time.time() - 3600; os.utime(os.path.join(d, stem + '_backup'), (old, old))
    assert S.side_files(f) == []


def test_cfb_fat_all_free_and_dir_sector_free_are_damaged(d):
    f = os.path.join(d, 'c.rvt'); b = bytearray(mini_cfb())
    b[512:1024] = struct.pack('<128I', *([0xFFFFFFFF] * 128)); open(f, 'wb').write(b)
    with pytest.raises(S.Damaged): S.cfb_check(f)
    b = bytearray(mini_cfb()); struct.pack_into('<I', b, 48, 3); b[512 + 12:512 + 16] = struct.pack('<I', 0xFFFFFFFF); open(f, 'wb').write(b)
    with pytest.raises(S.Damaged): S.cfb_check(f)


def test_run_relative_and_symlinked_dir_paths_are_guarded(d, capsys, monkeypatch):
    real = os.path.join(d, 'real'); os.mkdir(real); f = os.path.join(real, 'm.rvt'); open(f, 'wb').write(mini_cfb()); t = time.time() - 100; os.utime(f, (t, t))
    os.symlink(real, os.path.join(d, 'lnk'))
    def touch(argv, say=print):
        st = os.stat(f); os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9)); return 0
    monkeypatch.chdir(d)
    for p in ('real/m.rvt', 'lnk/m.rvt', os.path.join(d, 'lnk', 'm.rvt')):
        os.utime(f, (t, t)); S._ACTIVE.clear()
        assert S.run([p, '--quiet-secs', '0'], touch) == 75, p
