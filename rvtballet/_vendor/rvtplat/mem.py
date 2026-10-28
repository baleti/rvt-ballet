"""Memory facts without /proc: process RSS and the usable memory budget (cgroup, job object, or RAM)."""
import os, sys


def rss_bytes():
    """resident set of this process in bytes (0 if unknown)"""
    try:
        import psutil
        return psutil.Process().memory_info().rss
    except Exception:
        pass
    if sys.platform.startswith('linux'):
        try:
            return int(open('/proc/self/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
        except Exception:
            return 0
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                            ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                            ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
            pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
            k = ctypes.WinDLL('kernel32', use_last_error=True); p = ctypes.WinDLL('psapi', use_last_error=True)
            k.GetCurrentProcess.restype = wintypes.HANDLE
            p.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            if p.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return int(pmc.WorkingSetSize)
        except Exception:
            pass
        return 0
    try:                                    # macOS: ru_maxrss is bytes (peak, close enough)
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        return 0


def total_ram_bytes():
    try:
        import psutil
        return psutil.virtual_memory().total
    except Exception:
        pass
    try:
        if sys.platform == 'win32':
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [('l', ctypes.c_ulong), ('load', ctypes.c_ulong), ('total', ctypes.c_ulonglong),
                            ('avail', ctypes.c_ulonglong), ('tp', ctypes.c_ulonglong), ('ap', ctypes.c_ulonglong),
                            ('tv', ctypes.c_ulonglong), ('av', ctypes.c_ulonglong), ('ae', ctypes.c_ulonglong)]
            m = MS(); m.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.total)
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except Exception:
        return 0


def cgroup_limit_bytes():
    """Linux cgroup v2 memory.max of this process, or None"""
    try:
        cg = open('/proc/self/cgroup').read().strip().split('::')[-1]
        lim = open('/sys/fs/cgroup%s/memory.max' % cg).read().strip()
        return None if lim == 'max' else int(lim)
    except Exception:
        return None


def limit_gb(default_fraction=0.5):
    """memory budget for this process in GB: cgroup limit if capped, else a fraction of RAM; env RVTPLAT_MEM_GB wins"""
    e = os.environ.get('RVTPLAT_MEM_GB')
    if e:
        return float(e)
    c = cgroup_limit_bytes()
    if c:
        return c / 2 ** 30
    t = total_ram_bytes()
    return (t * default_fraction / 2 ** 30) if t else 4.0
