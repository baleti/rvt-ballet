"""Best-effort 'is this file open in another process?' (Linux: /proc/<pid>/fd; other platforms: unknown -> []). An in-place save replaces the file by rename: a program that still has the old file open (Revit, a viewer) keeps the old copy and silently overwrites our edit when it saves. Returns the NAMES of the other processes (never paths); at most `budget` seconds are spent."""
import os, time


def open_elsewhere(path, budget=1.5):
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
