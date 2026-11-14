"""measure_tree.py CMD...: run CMD, report wall, CPU (user+sys of the whole tree), peak summed RSS of the process tree (double counts shared pages),
peak and average cores busy (sampled every 50 ms from /proc). Output on stderr as one line starting with MEASURE:"""
import os, sys, time, subprocess, resource

TICK = os.sysconf('SC_CLK_TCK'); PG = os.sysconf('SC_PAGE_SIZE')


def tree(root):
    kids = {}
    for d in os.listdir('/proc'):
        if not d.isdigit(): continue
        try:
            s = open('/proc/%s/stat' % d).read(); r = s.rsplit(')', 1)[1].split()
            kids.setdefault(int(r[1]), []).append(int(d))
        except Exception: pass
    out = []; st = [root]
    while st:
        p = st.pop(); out.append(p); st.extend(kids.get(p, []))
    return out


def sample(pids):
    rss = 0; cpu = 0
    for p in pids:
        try:
            r = open('/proc/%d/stat' % p).read().rsplit(')', 1)[1].split()
            cpu += int(r[11]) + int(r[12]); rss += int(r[21]) * PG
        except Exception: pass
    return rss, cpu


def main():
    t0 = time.time(); pr = subprocess.Popen(sys.argv[1:])
    peak = 0; dead_cpu = {}; last = None; peak_cores = 0.0; seen = {}; peak_pss = 0; k = 0
    while pr.poll() is None:
        pids = tree(pr.pid); rss = 0; now = time.time()
        cur = {}
        for p in pids:
            try:
                r = open('/proc/%d/stat' % p).read().rsplit(')', 1)[1].split()
                cur[p] = (int(r[11]) + int(r[12])); rss += int(r[21]) * PG
            except Exception: pass
        peak = max(peak, rss); k += 1
        if k % 4 == 0:                    # PSS: shared pages split between the processes that map them (forked workers share the decoder/schema pages)
            pss = 0
            for p in pids:
                try:
                    for l in open('/proc/%d/smaps_rollup' % p):
                        if l.startswith('Pss:'): pss += int(l.split()[1]) << 10; break
                except Exception: pass
            peak_pss = max(peak_pss, pss)
        if last is not None:
            tl, prev = last; d = sum(v - prev.get(p, 0) for p, v in cur.items() if v >= prev.get(p, 0))
            if now - tl > 0: peak_cores = max(peak_cores, d / TICK / (now - tl))
        seen.update(cur); last = (now, cur)
        time.sleep(0.05)
    wall = time.time() - t0; ru = resource.getrusage(resource.RUSAGE_CHILDREN); cpu = ru.ru_utime + ru.ru_stime
    sys.stderr.write('MEASURE: wall %.2f s, cpu %.1f s (user %.1f, sys %.1f), avg cores %.1f, peak cores %.1f (100 ms samples), peak tree RSS %d MB (sum, double counts shared pages), peak tree PSS %d MB (200 ms samples), rc %d\n'
                     % (wall, cpu, ru.ru_utime, ru.ru_stime, cpu / wall, peak_cores, peak >> 20, peak_pss >> 20, pr.returncode))
    sys.exit(pr.returncode)


if __name__ == '__main__': main()
