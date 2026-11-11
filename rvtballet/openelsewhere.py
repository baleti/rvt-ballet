"""Best-effort 'is this file open in another process?' (Linux: /proc/<pid>/fd; other platforms: unknown -> []). An in-place save replaces the file by rename: a program that still has the old file open (Revit, a viewer) keeps the old copy and silently overwrites our edit when it saves. Returns the NAMES of the other processes (never paths); at most `budget` seconds are spent."""
import os, time


def _win_rm(path):
    """Windows: Restart Manager (RmStartSession / RmRegisterResources / RmGetList) names the applications that hold the file. UNTESTED on a real Windows host (written from the documented API, any failure returns [])."""
    import ctypes
    from ctypes import wintypes
    rm = ctypes.WinDLL('Rstrtmgr.dll'); h = wintypes.DWORD(); key = ctypes.create_unicode_buffer(33)
    if rm.RmStartSession(ctypes.byref(h), 0, key) != 0: return []
    try:
        arr = (wintypes.LPCWSTR * 1)(os.path.abspath(path))
        if rm.RmRegisterResources(h, 1, arr, 0, None, 0, None) != 0: return []
        class UP(ctypes.Structure): _fields_ = [('pid', wintypes.DWORD), ('t', wintypes.FILETIME)]
        class PI(ctypes.Structure): _fields_ = [('Proc', UP), ('AppName', ctypes.c_wchar * 256), ('Svc', ctypes.c_wchar * 64), ('AppType', ctypes.c_uint), ('Status', ctypes.c_ulong), ('TsSession', wintypes.DWORD), ('Restartable', wintypes.BOOL)]
        need = wintypes.UINT(0); have = wintypes.UINT(8); reasons = wintypes.DWORD(0); info = (PI * 8)()
        rm.RmGetList(h, ctypes.byref(need), ctypes.byref(have), info, ctypes.byref(reasons))
        return sorted(set(info[i].AppName[:30] for i in range(min(have.value, 8)) if info[i].Proc.pid != os.getpid()))
    finally: rm.RmEndSession(h)


def open_elsewhere(path, budget=1.5):
    if os.name == 'nt':
        try: return _win_rm(path)
        except Exception: return []
    if not os.path.isdir('/proc/self/fd'): return []
    try: target = os.path.realpath(path)
    except OSError: return []
    me = os.getpid(); out = []; t0 = time.time()
    try: pids = [p for p in os.listdir('/proc') if p.isdigit() and int(p) != me]
    except OSError: return []
    for p in pids:
        if time.time() - t0 > budget: break
        try:
            for fd in os.listdir('/proc/%s/fd' % p):
                try:
                    if os.readlink('/proc/%s/fd/%s' % (p, fd)) == target:
                        try: out.append(open('/proc/%s/comm' % p).read().strip()[:30])
                        except OSError: out.append('pid %s' % p)
                        break
                except OSError: continue
        except OSError: continue      # not ours (permission) or gone
    return sorted(set(out))
