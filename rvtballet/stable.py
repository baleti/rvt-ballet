"""Torn-read guard for .rvt files: never answer from a file that is being saved.

A Revit save (or a copy tool, a sync client, a 9p share) can change the file while a reader walks it. Pages from two versions then mix and the
answer is silently wrong. This module gives every reader the same three tools, all read-only and cheap:

  fingerprint(path)      size, mtime_ns, inode, device plus a hash of ~20 sampled blocks (head, tail, evenly spaced). Catches a same-size in-place
                         overwrite on a file system with a coarse mtime. Cost: a stat and ~100 KB of reads, independent of file size.
  wait_quiet(path)       do not start on a file modified in the last `quiet` seconds, or whose stat is still moving, or that has a fresh side file
                         next to it (Revit temp / backup copies); retry with backoff, then raise InUse.
  guard(path)            context manager: wait_quiet, fingerprint, run the query, fingerprint again; any difference raises FileChanged.
  snapshot(path)         copy the file to a local temp dir, accepting the copy only if the source fingerprint is identical before and after the
                         copy and the copy equals the source (size + sampled blocks); the query then runs on the copy. Deleted on exit.
  cfb_check(path)        header and FAT sanity (signature, sector size, every used sector lies inside the file): catches a truncated or half
                         written file that stats cleanly.

What is NOT guaranteed (see docs/stable-read.md): a writer that changes bytes between the sampled blocks without changing size or mtime_ns
and that finishes before the second fingerprint is only caught by the full-copy comparison of --snapshot (size/mtime exactness is up to the file system).
"""
import os, sys, time, hashlib, struct, shutil, tempfile, contextlib, errno

BLOCK = 4096
NSAMPLES = 16
HEAD = 65536
DEFAULT_QUIET = 5.0
ENV_QUIET = 'RVTBALLET_QUIET'      # seconds, 0 disables the quiet period
ENV_OFF = 'RVTBALLET_NO_STABLE'    # '1' disables the guard (tests that measure the raw reader only)


class FileChanged(RuntimeError):
    """the file was modified or replaced while it was being read: no answer is given"""
    def __init__(s, path, why):
        RuntimeError.__init__(s, '%s changed during read (%s): retry' % (os.path.basename(path), why)); s.why = why; s.path = path


class InUse(RuntimeError):
    """the file looks like it is being written (recent modification, moving size, fresh side files) and did not settle within the retry budget"""
    def __init__(s, path, why):
        RuntimeError.__init__(s, '%s is being saved or was modified moments ago (%s): retry later or use --snapshot' % (os.path.basename(path), why)); s.why = why; s.path = path


class Damaged(RuntimeError):
    """the file fails a structural check (truncated, bad header)"""
    def __init__(s, path, why):
        RuntimeError.__init__(s, '%s is not a complete .rvt (%s)' % (os.path.basename(path), why)); s.why = why; s.path = path


def quiet_default():
    try: return float(os.environ.get(ENV_QUIET, DEFAULT_QUIET))
    except ValueError: return DEFAULT_QUIET


def enabled(): return os.environ.get(ENV_OFF) != '1'


def _offsets(size):
    """block offsets sampled: the head, the tail and NSAMPLES evenly spaced blocks (deterministic, depends only on size)"""
    if size <= HEAD + 2 * BLOCK * NSAMPLES: return [(0, size)]
    offs = [(0, HEAD), (max(0, size - HEAD), HEAD)]
    step = (size - HEAD) // (NSAMPLES + 1)
    offs += [(i * step + (i * 997) % BLOCK, BLOCK) for i in range(1, NSAMPLES + 1)]
    return offs


def sample_hash(fd, size):
    h = hashlib.blake2b(digest_size=16)
    for off, ln in _offsets(size):
        b = os.pread(fd, ln, off); h.update(struct.pack('<QQ', off, len(b))); h.update(b)
    return h.hexdigest()


class Fingerprint(tuple):
    """(size, mtime_ns, ino, dev, sample hash) with a readable diff"""
    FIELDS = ('size', 'modification time', 'inode', 'device', 'sampled content')
    def diff(s, o):
        return [n for n, a, b in zip(s.FIELDS, s, o) if a != b and not (n in ('inode', 'device') and (not a or not b))]


def fingerprint(path, fd=None):
    """read-only fingerprint of the file at `path` (or of the open handle fd). Raises FileChanged-style OSError if it cannot be read."""
    own = fd is None
    if own: fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd); return Fingerprint((st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev, sample_hash(fd, st.st_size)))
    finally:
        if own: os.close(fd)


def path_stamp(path):
    st = os.stat(path); return (st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev)


_SIDE_SUFFIX = ('.tmp', '.temp', '.part', '.partial', '.crdownload', '.lock', '~', '.bak')


def side_files(path, within=30.0, now=None):
    """names of files next to `path` that look like a save in progress and were touched in the last `within` seconds: Revit writes a temp copy
    (<name>.<4 digits>.rvt backups, <name>.rvt.<random> or *.tmp) in the same folder. Not exhaustive: on a share that hides them nothing is seen."""
    d = os.path.dirname(os.path.abspath(path)) or '.'; base = os.path.basename(path); stem, ext = os.path.splitext(base)
    now = time.time() if now is None else now; out = []
    try: names = os.listdir(d)
    except OSError: return out
    for n in names:
        if n == base or not (n.startswith(base) or n.startswith(stem)): continue
        low = n.lower(); tail = low[len(stem):]
        fresh = low.endswith(_SIDE_SUFFIX) or n.startswith(base + '.') or (tail[:1] == '.' and tail[1:5].isdigit())
        if not fresh: continue
        try: age = now - os.stat(os.path.join(d, n)).st_mtime
        except OSError: continue
        if -60 <= age <= within: out.append(n)
    return sorted(out)


def wait_quiet(path, quiet=None, retries=6, backoff=1.0, settle=0.2, sleep=time.sleep, clock=time.time):
    """return when the file has not been modified for `quiet` seconds, its stat is identical across `settle` seconds and no fresh side file exists.
    Otherwise sleep (backoff doubling) and retry; raises InUse after `retries`. quiet=0 only runs the settle check."""
    quiet = quiet_default() if quiet is None else quiet; why = ''
    for attempt in range(retries + 1):
        try: a = path_stamp(path)
        except OSError as ex: raise InUse(path, 'cannot stat it: %s' % ex)
        age = clock() - a[1] / 1e9; why = ''
        skew = age < -300                      # mtime far in the future = clock skew of a share: the age tells nothing, the settle check below still applies
        if quiet and age < quiet and not skew: why = 'modified %.1f s ago' % age
        if not why:
            if settle and not (quiet and age >= quiet and not skew): sleep(settle)       # an old file needs no settle wait (the guard's closing fingerprint covers a silent writer)
            try: b = path_stamp(path)
            except OSError as ex: raise InUse(path, 'cannot stat it: %s' % ex)
            if a[:2] != b[:2]: why = 'size or modification time still changing'
            elif quiet and side_files(path, within=max(quiet, 30.0), now=clock()): why = 'fresh side file(s): %s' % ', '.join(side_files(path, within=max(quiet, 30.0), now=clock())[:3])
        if not why: return b
        if attempt == retries: break
        sleep(min(backoff * (2 ** attempt), 30.0) if quiet else backoff)
    raise InUse(path, why)


def cfb_check(path, fd=None):
    """cheap structural check of a compound file: signature, sector size, FAT readable and every sector in use inside the file. -> None or raises Damaged"""
    own = fd is None
    if own: fd = os.open(path, os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        if size == 0: raise Damaged(path, 'zero length')
        h = os.pread(fd, 512, 0)
        if len(h) < 512 or h[:8] != bytes.fromhex('D0CF11E0A1B11AE1'): raise Damaged(path, 'no compound file signature')
        shift = struct.unpack_from('<H', h, 30)[0]
        if shift not in (9, 12): raise Damaged(path, 'bad sector size')
        ss = 1 << shift; nfat = struct.unpack_from('<I', h, 44)[0]; difat_start, ndifat = struct.unpack_from('<II', h, 68)
        fat_secs = [x for x in struct.unpack_from('<109I', h, 76) if x < 0xFFFFFFFA][:nfat]
        d = difat_start; guard = 0
        while len(fat_secs) < nfat and d < 0xFFFFFFFA and ndifat and guard <= ndifat:
            b = os.pread(fd, ss, (d + 1) * ss)
            if len(b) < ss: raise Damaged(path, 'truncated DIFAT')
            ent = struct.unpack('<%dI' % (ss // 4), b); fat_secs += [x for x in ent[:-1] if x < 0xFFFFFFFA]; d = ent[-1]; guard += 1
        fat_secs = fat_secs[:nfat]
        if len(fat_secs) != nfat: raise Damaged(path, 'FAT sector list incomplete')
        last = -1
        for k, fs in enumerate(fat_secs):
            b = os.pread(fd, ss, (fs + 1) * ss)
            if len(b) < ss: raise Damaged(path, 'truncated: FAT sector %d beyond end of file' % fs)
            for j in range(ss // 4 - 1, -1, -1):          # highest sector id in use (not FREE 0xFFFFFFFF) of this FAT sector
                if struct.unpack_from('<I', b, 4 * j)[0] != 0xFFFFFFFF: last = max(last, k * (ss // 4) + j); break
        if last >= 0 and (last + 2) * ss > size: raise Damaged(path, 'truncated: sector %d needs %d bytes, file has %d' % (last, (last + 2) * ss, size))
    finally:
        if own: os.close(fd)


@contextlib.contextmanager
def guard(path, quiet=None, retries=6, check=True):
    """with guard(path) as g: <read the file, any way you like>; the block raises FileChanged on exit if the file differs from its entry fingerprint.
    g.fingerprint is the entry fingerprint. An exception raised inside the block while the file changed is replaced by FileChanged (a torn read
    often shows up as a parse error: the cause is the change, not the file)."""
    if not enabled():
        yield None; return
    wait_quiet(path, quiet=quiet, retries=retries)
    g = _Guard(path); g.fingerprint = fingerprint(path)
    if check: cfb_check(path)
    try:
        yield g
    except BaseException as ex:
        if isinstance(ex, (KeyboardInterrupt, SystemExit, FileChanged)): raise
        try: g.verify()
        except FileChanged as ch: raise ch from ex
        raise
    else:
        g.verify()


class _Guard:
    def __init__(s, path): s.path = path; s.fingerprint = None
    def verify(s):
        try: now = fingerprint(s.path)
        except OSError as ex: raise FileChanged(s.path, 'cannot read it any more: %s' % ex)
        d = s.fingerprint.diff(now)
        if d: raise FileChanged(s.path, '%s changed' % ' and '.join(d))


def _free(path):
    st = os.statvfs(path); return st.f_bavail * st.f_frsize


@contextlib.contextmanager
def snapshot(path, tmpdir=None, attempts=3, quiet=None, chunk=8 << 20, log=None):
    """copy the file to a private temp dir and yield the copy's path. The copy is accepted only when the source fingerprint is identical before and
    after the copy and the copy has the same size and sampled content; otherwise the copy is repeated (after the quiet period) up to `attempts`.
    The copy is removed on exit, also on error. Needs free disk space of the file size (checked first)."""
    say = log or (lambda m: None); src = os.path.abspath(path); tmp = None
    try:
        for n in range(attempts):
            wait_quiet(src, quiet=quiet)
            size = os.stat(src).st_size
            base = tmpdir or tempfile.gettempdir()
            if _free(base) < size + (64 << 20): raise OSError(errno.ENOSPC, 'not enough free space in %s for a %d MB snapshot' % (base, size >> 20))
            tmp = tempfile.mkdtemp(prefix='rvtsnap-', dir=base); os.chmod(tmp, 0o700); dst = os.path.join(tmp, os.path.basename(src))
            f0 = fingerprint(src); t0 = time.time()
            with open(src, 'rb') as a, open(dst, 'xb') as b:
                while True:
                    buf = a.read(chunk)
                    if not buf: break
                    b.write(buf)
            f1 = fingerprint(src); fd = fingerprint(dst)
            ok = not f0.diff(f1) and fd[0] == f0[0] and fd[4] == f0[4]
            say('snapshot %d: %d MB in %.1f s, %s' % (n + 1, size >> 20, time.time() - t0, 'stable' if ok else 'source changed during the copy'))
            if ok:
                try: cfb_check(dst)
                except Damaged: raise
                yield dst; return
            shutil.rmtree(tmp, ignore_errors=True); tmp = None
        raise InUse(src, 'changed during every one of %d snapshot attempts' % attempts)
    finally:
        if tmp: shutil.rmtree(tmp, ignore_errors=True)


_ACTIVE = []
_EXT = ('.rvt', '.rte', '.rfa', '.rft')


def run(argv, fn, say=print):
    """entry-point wrapper used by the read-only commands: fn(argv, say) runs with every .rvt/.rte/.rfa path argument guarded (quiet period, closing
    fingerprint). Options understood and removed here: --snapshot (query a verified private copy), --quiet-secs N (default 5, 0 = off).
    A change during the read, a file still being saved and a half-written file end in a one-line message and exit 75 / 75 / 1, never in an answer."""
    argv = list(argv); snap = False; quiet = None; out = []; i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--snapshot': snap = True
        elif a == '--quiet-secs' and i + 1 < len(argv):
            try: quiet = float(argv[i + 1])
            except ValueError: print('rvt-ballet: --quiet-secs needs a number', file=sys.stderr); return 2
            i += 1
        elif a.startswith('--quiet-secs='):
            try: quiet = float(a.split('=', 1)[1])
            except ValueError: print('rvt-ballet: --quiet-secs needs a number', file=sys.stderr); return 2
        else: out.append(a)
        i += 1
    argv = out
    if _ACTIVE or not enabled(): return fn(argv, say)
    idx = [k for k, a in enumerate(argv) if a.lower().endswith(_EXT) and os.path.isfile(a)]
    if not idx: return fn(argv, say)
    _ACTIVE.append(1)
    try:
        with contextlib.ExitStack() as st:
            for k in idx:
                p = argv[k]
                if snap:
                    argv[k] = st.enter_context(snapshot(p, quiet=quiet, log=lambda m: print('rvt-ballet: ' + m, file=sys.stderr)))
                else:
                    st.enter_context(guard(p, quiet=quiet))
            return fn(argv, say)
    except (FileChanged, InUse) as ex:
        print('rvt-ballet: %s' % ex, file=sys.stderr); return 75
    except Damaged as ex:
        print('rvt-ballet: %s' % ex, file=sys.stderr); return 1
    finally:
        _ACTIVE.pop()
