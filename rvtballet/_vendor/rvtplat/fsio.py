"""Safe file writes that behave the same on Windows, macOS and Linux.

Windows specifics handled here:
    indexer, backup, a second viewer) holds the destination open: retry with exponential backoff.
  * read-only attribute on the destination (os.replace refuses): cleared when `clear_readonly`.
  * long paths (>259 chars): extended-length prefix via long_path().
  * unicode paths: all functions take str; no ANSI APIs.
  * OneDrive/Dropbox placeholders: the destination is replaced, never opened for in-place update.
Data is flushed and fsync'ed before the rename, and the directory is fsync'ed on POSIX, so a crash or
power loss leaves either the old or the new file, never a torn one."""
import os, sys, time, stat, tempfile, errno

_WIN = sys.platform == 'win32'
# Windows sharing/permission errors that mean "somebody else has it open right now"
_WIN_BUSY = {5, 32, 33, 1224}


def long_path(p):
    """extended-length form on Windows for paths that would exceed MAX_PATH; identity elsewhere"""
    if not _WIN:
        return p
    p = os.path.abspath(p)
    if p.startswith('\\\\?\\'):
        return p
    if p.startswith('\\\\'):
        return '\\\\?\\UNC\\' + p[2:]
    return '\\\\?\\' + p if len(p) >= 248 else p


def _busy(e):
    if isinstance(e, PermissionError):
        return True
    return (w in _WIN_BUSY) or (e.errno in (errno.EACCES, errno.EBUSY, errno.EPERM) and _WIN)


def replace_retry(src, dst, tries=12, delay=0.02, max_delay=0.5, clear_readonly=False, _sleep=time.sleep):
    """os.replace with backoff on Windows-style sharing violations (about 3 s total at the defaults)"""
    src, dst = long_path(src), long_path(dst)
    d = delay
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except OSError as e:
            if not _busy(e) or i == tries - 1:
                raise
            if clear_readonly:
                try:
                    os.chmod(dst, os.stat(dst).st_mode | stat.S_IWRITE)
                except OSError:
                    pass
            _sleep(d)
            d = min(d * 2, max_delay)


def _fsync_dir(path):
    if _WIN:
        return
    try:
        fd = os.open(path or '.', os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def atomic_write(path, data, mode=None, encoding='utf-8', newline=None, clear_readonly=False, fsync=True):
    """Write `data` (bytes, or str encoded with `encoding`) to `path` atomically; returns path.
    The temporary file lives in the destination directory (same volume, so the rename is atomic).
    str is written with newline translation disabled unless `newline` is given."""
    path = os.fspath(path)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(long_path(d), exist_ok=True)
    if isinstance(data, str):
        data = data.encode(encoding)
        if newline not in (None, '', '\n'):
            data = data.replace(b'\n', newline.encode(encoding))
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path)[:40] + '.', suffix='.tmp', dir=long_path(d))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        elif os.path.exists(long_path(path)):
            try:
                os.chmod(tmp, stat.S_IMODE(os.stat(long_path(path)).st_mode) | stat.S_IWRITE)
            except OSError:
                pass
        replace_retry(tmp, path, clear_readonly=clear_readonly)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    if fsync:
        _fsync_dir(d)
    return path


def atomic_write_with(path, writer, **kw):
    """writer(fileobj) fills a binary temp file (for pickle.dump / large streams); then the same replace"""
    import io
    buf = io.BytesIO()
    writer(buf)
    return atomic_write(path, buf.getvalue(), **kw)


def atomic_write_stream(path, writer, clear_readonly=False, fsync=True):
    """like atomic_write_with but streams straight to the temp file (no copy in RAM, for big caches)"""
    path = os.fspath(path)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(long_path(d), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path)[:40] + '.', suffix='.tmp', dir=long_path(d))
    try:
        with os.fdopen(fd, 'wb') as f:
            writer(f)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        replace_retry(tmp, path, clear_readonly=clear_readonly)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    if fsync:
        _fsync_dir(d)
    return path


def safe_save(path, data, keep_backup=True, **kw):
    """overwrite a USER document (.rvt/.dwg): atomic_write, plus a one-generation `.bak` copy of the old
    file next to it (copy, not rename, so the original is never absent). Backup failures never block the save."""
    import shutil
    path = os.fspath(path)
    if keep_backup and os.path.isfile(long_path(path)):
        try:
            shutil.copy2(long_path(path), long_path(path + '.bak'))
        except OSError:
            pass
    return atomic_write(path, data, clear_readonly=False, **kw)


def read_retry(path, mode='rb', tries=8, delay=0.02, **kw):
    """open+read whole file, retrying while a scanner/indexer holds an exclusive lock (Windows)"""
    d = delay
    for i in range(tries):
        try:
            with open(long_path(path), mode, **kw) as f:
                return f.read()
        except OSError as e:
            if not _busy(e) or i == tries - 1:
                raise
            time.sleep(d)
            d = min(d * 2, 0.5)


def is_cloud_placeholder(path):
    """True for a OneDrive/Dropbox 'online-only' file whose content is not on disk yet (Windows reparse /
    FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS 0x400000, OFFLINE 0x1000). Reading it triggers a download."""
    if not _WIN:
        return False
    try:
        a = os.stat(long_path(path)).st_file_attributes
    except (OSError, AttributeError):
        return False
    return bool(a & (0x400000 | 0x1000 | 0x40000))


def is_readonly(path):
    try:
        return not os.access(long_path(path), os.W_OK)
    except OSError:
        return False
