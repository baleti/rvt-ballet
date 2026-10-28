"""Run a child process with a memory cap and lowered priority, on every OS.

Linux: systemd-run --user --scope (MemoryMax, MemorySwapMax=0) when available, else RLIMIT_AS via preexec.
Windows: Job Object (process memory limit, kill-on-close) + BELOW_NORMAL priority.
macOS: nice (no hard memory cap is available; documented limitation)."""
import os, sys, shutil, subprocess


def _win_job(pid_handle_proc, mem_bytes):
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)

    class BASIC(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                    ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [('a', ctypes.c_uint64)] * 6

    class EXT(ctypes.Structure):
        _fields_ = [('Basic', BASIC), ('Io', IO), ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t),
                    ('PeakJobMemoryUsed', ctypes.c_size_t)]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    job = k.CreateJobObjectW(None, None)
    info = EXT()
    # 0x100 PROCESS_MEMORY, 0x2000 KILL_ON_JOB_CLOSE
    info.Basic.LimitFlags = 0x2000 | (0x100 if mem_bytes else 0)
    info.ProcessMemoryLimit = int(mem_bytes or 0)
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    if not k.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError(ctypes.get_last_error(), 'SetInformationJobObject')
    h = int(pid_handle_proc._handle)
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    if not k.AssignProcessToJobObject(job, h):
        raise OSError(ctypes.get_last_error(), 'AssignProcessToJobObject')
    return job                      # keep the handle alive as long as the child should be capped


def capped_argv(cmd, mem_gb=None, nice=10):
    """POSIX argv prefix (systemd-run/nice); Windows returns cmd unchanged (use popen_capped)"""
    cmd = list(cmd)
    if sys.platform == 'win32':
        return cmd
    if sys.platform.startswith('linux') and mem_gb and shutil.which('systemd-run') \
            and os.environ.get('RVT_NO_CAP') != '1':
        pre = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=%dM' % int(mem_gb * 1024), '-p', 'MemorySwapMax=0']
        return pre + (['nice', '-n', str(nice)] if nice else []) + cmd
    return (['nice', '-n', str(nice)] if nice and shutil.which('nice') else []) + cmd


def popen_capped(cmd, mem_gb=None, nice=10, **kw):
    """Popen with memory cap + low priority; returns the Popen (p._rvtplat_job holds the Windows job)"""
    if sys.platform == 'win32':
        kw['creationflags'] = kw.get('creationflags', 0) | 0x00004000       # BELOW_NORMAL_PRIORITY_CLASS
        p = subprocess.Popen(list(cmd), **kw)
        try:
            p._rvtplat_job = _win_job(p, int(mem_gb * 2 ** 30) if mem_gb else 0)
        except Exception:
            p._rvtplat_job = None                                             # cap is best effort
        return p
    argv = capped_argv(cmd, mem_gb, nice)
    if argv[:1] != ['systemd-run'] and mem_gb and sys.platform.startswith('linux'):
        import resource
        lim = int(mem_gb * 2 ** 30)
        kw['preexec_fn'] = lambda: resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    return subprocess.Popen(argv, **kw)


def run_capped(cmd, mem_gb=None, nice=10, **kw):
    timeout = kw.pop('timeout', None)
    capture = kw.pop('capture_output', False)
    if capture:
        kw['stdout'] = kw['stderr'] = subprocess.PIPE
    p = popen_capped(cmd, mem_gb, nice, **kw)
    out, err = p.communicate(timeout=timeout)
    return subprocess.CompletedProcess(p.args, p.returncode, out, err)


def call_with_timeout(fn, seconds, *a, **k):
    """run fn in a daemon thread; raise TimeoutError if it does not finish (replaces SIGALRM, portable;
    the thread is abandoned, not killed: use only for pure computations that may spin)"""
    import threading
    box = {}

    def run():
        try:
            box['v'] = fn(*a, **k)
        except BaseException as e:
            box['e'] = e
    t = threading.Thread(target=run, daemon=True); t.start(); t.join(seconds)
    if t.is_alive():
        raise TimeoutError('timed out after %ss' % seconds)
    if 'e' in box:
        raise box['e']
    return box['v']


def pid_alive(pid):
    """True when a process with this pid exists. POSIX: kill(pid, 0). Windows: OpenProcess + exit code
    (os.kill(pid, 0) on Windows sends a console control event, never use it as a probe)."""
    pid = int(pid)
    if pid <= 0:
        return False
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        h = k.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() == 5          # access denied: exists
        try:
            code = wintypes.DWORD()
            k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259     # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
