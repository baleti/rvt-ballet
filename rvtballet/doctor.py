"""rvt-ballet doctor: one-screen health check (environment, savegate policy, ledger, Revit VM lanes, memory guard).
Read-only. Anything it cannot see on this machine is reported as 'n/a', never as a pass. Exit 0 = no FAIL, 1 = at least one FAIL."""
import os, sys, json, glob, shutil, subprocess, collections

def _sh(cmd, t=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t); return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 127, str(e)

def _memavail_mb():
    try:
        for l in open('/proc/meminfo'):
            if l.startswith('MemAvailable'): return int(l.split()[1]) // 1024
    except OSError: pass
    return None

def main(argv=None):
    rows = []
    def add(level, what, msg): rows.append((level, what, msg))
    home = os.path.expanduser('~')
    ds = os.environ.get('RVT_DEMO_STATE') or os.path.join(home, 'demo-state')
    # 1 environment
    add('ok', 'python', sys.version.split()[0])
    for mod in ('numpy', 'olefile'):
        try: __import__(mod); add('ok', 'dep ' + mod, 'importable')
        except Exception: add('warn', 'dep ' + mod, 'missing (some commands need it)')
    # 2 savegate and policy
    try:
        from . import save as _save; sg = _save._import()
        if sg is None: add('fail', 'savegate', 'not importable (in-place save and restore are unavailable)')
        else: add('ok', 'savegate', 'importable (' + os.path.dirname(getattr(sg, '__file__', '?')) + ')')
    except Exception as e:
        add('fail', 'savegate', 'check failed: %s' % e)
    ow = os.environ.get('RVTBALLET_ALLOW_OVERWRITE') == '1'
    add('ok', 'SAVE! policy', 'in-place overwrite ON' if ow else 'in-place overwrite OFF (default; edit writes a NEW file with -o)')
    en = sorted(k for k in os.environ if k.startswith('RVTBALLET_ENABLE_') and os.environ[k] == '1')
    add('ok', 'experimental ops', ', '.join(en) if en else 'none enabled')
    # 3 evidence ledger
    lg = os.path.join(ds, 'rvt-edit', 'ledger.jsonl')
    if os.path.exists(lg):
        last = {}
        for l in open(lg, errors='replace'):
            try: d = json.loads(l)
            except ValueError: continue
            if d.get('cat') and d.get('item'): last[(d['cat'], d['item'])] = d.get('result')
        c = collections.Counter(last.values()); fails = sorted(k for k, v in last.items() if v == 'FAIL')
        add('ok' if c.get('PASS') else 'warn', 'ledger', '%d items: %d PASS, %d FAIL (latest record per item)' % (len(last), c.get('PASS', 0), c.get('FAIL', 0)))
        cats = collections.Counter(k[0] for k in fails)
        if cats: add('warn', 'open FAIL by category', '; '.join('%s: %d' % kv for kv in cats.most_common(5)))
    else:
        add('na', 'ledger', 'n/a (no %s on this host)' % lg)
    # 4 fixtures
    sd = os.environ.get('RVT_SAMPLES') or os.path.join(home, 'rvt-samples')
    if os.path.isdir(sd):
        files = glob.glob(os.path.join(sd, '**', '*.rvt'), recursive=True)
        yrs = collections.Counter()
        for f in files:
            n = os.path.basename(f)
            for y in range(2020, 2027):
                if str(y) in n: yrs[y] += 1
        add('ok' if files else 'warn', 'fixtures', '%d .rvt in %s; year tags in names: %s' % (len(files), sd, dict(sorted(yrs.items())) or 'none'))
    else:
        add('na', 'fixtures', 'n/a (no %s)' % sd)
    # 5 lanes and memory guard (remote-host only: the Revit VMs live there)
    lc = os.path.join(ds, 'rvt-lanes', 'lanectl')
    mem = _memavail_mb()
    try:
        l1 = os.getloadavg()[0]; nc = os.cpu_count() or 1
        add('ok' if l1 < nc else ('warn' if l1 < 2 * nc else 'fail'), 'load', '%.1f on %d CPUs (lanes and edits slow down sharply above CPU count; edit of a 22 MB file took 3-5 min at load 50-70)' % (l1, nc))
    except (OSError, AttributeError): pass
    if mem is not None: add('ok' if mem >= 8192 else 'fail', 'memory', 'MemAvailable %d MB (lane guard floor 8192, start gate 19456)' % mem)
    if os.path.exists(lc):
        rc, o = _sh(['bash', lc, 'status'])
        for l in o.splitlines()[1:]:
            lvl = 'ok' if ' up' in l else 'warn'
            if 'lane1' in l: lvl = 'ok' if ' up' in l else 'na'
            add(lvl, l.split(':')[0].split(' (')[0], l.split(':', 1)[-1].strip() or l)
        vq = os.path.join(home, 'rvt-research', 'write-lab', 'campaign', 'vmq')
        if os.path.isdir(vq):
            n = len(os.listdir(vq)); add('ok' if n < 8 else 'warn', 'oracle queue', '%d tickets waiting for a Revit lane (each job ~7+ min; FIFO, one ticket per file)' % n)
        rc, o = _sh(['bash', '-c', "ps -eo args | grep -E 'lanectl.* (guard|auto)' | grep -v grep | head -3"])
        add('ok', 'lane guard/auto loop', 'running' if o else 'not running now (guard only acts when a loop or cron calls `lanectl guard`)')
        gl = os.path.join(ds, 'rvt-lanes', 'guard.log')
        if os.path.exists(gl):
            ls = open(gl, errors='replace').read().splitlines()
            add('warn' if ls else 'ok', 'guard.log', '%d stop events, last: %s' % (len(ls), (ls[-1][:90] if ls else '-')))
        rc, o = _sh(['bash', '-c', "journalctl -k --since -24h 2>/dev/null | grep -i 'Killed process' | grep -c qemu"])
        n = o.strip().splitlines()[-1] if o.strip() else '?'
        add('ok' if n == '0' else 'fail', 'kernel OOM kills of qemu (24h)', n)
    else:
        add('na', 'revit lanes', 'n/a: lane tooling not on this host (Revit VMs run on remote-host; run `rvt-ballet doctor` there)')
    icon = {'ok': 'OK  ', 'warn': 'WARN', 'fail': 'FAIL', 'na': 'n/a '}
    for lv, w, m in rows: print('%s %-30s %s' % (icon[lv], w, m))
    nf = sum(1 for r in rows if r[0] == 'fail')
    print('\n%d FAIL, %d WARN. Savegate/edit gaps: `rvt-ballet edit --list-ops`. Details: demo-state/RVT-BALLET-STATUS.md' % (nf, sum(1 for r in rows if r[0] == 'warn')))
    return 1 if nf else 0
