"""demo hardening sweep: convert EVERY corpus file (2017-2026, .rvt + .rte) exactly like `rvt-view` does, one at a time, each in its own subprocess with a timeout;
one JSON line per file in ~/.cache/rvt-viewer/sweep.jsonl (status ok / fail / timeout / killed, seconds, stage timings, elements, triangles, fidelity buckets, error tail).
usage: tools/sweep.py [FILES...]   (default: all of ~/rvt-research/corpus; files already in the jsonl are skipped, RVT_SWEEP_REDO=1 redoes them)
host1: h1run run vsweep --env occ --dir ~/src/rvt-viewer -- python tools/sweep.py   then   h1run pull .cache/rvt-viewer/sweep.jsonl ; tools/sweep_table.py"""
import sys, os, json, time, glob, subprocess, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.expanduser(os.environ.get('RVT_SWEEP_OUT', '~/.cache/rvt-viewer/sweep.jsonl')); WORK = os.path.expanduser('~/.cache/rvt-viewer/sweep-work')
TIMEOUT = int(os.environ.get('RVT_SWEEP_TIMEOUT', '1200'))

def main(files):
    done = set()
    if os.path.exists(OUT) and not os.environ.get('RVT_SWEEP_REDO'):
        for l in open(OUT):
            try: done.add(json.loads(l)['src'])
            except Exception: pass
    os.makedirs(WORK, exist_ok=True)
    for f in files:
        f = os.path.abspath(f)
        if f in done: continue
        y = os.path.basename(os.path.dirname(f)) if 'samples-rfa' not in f else 'rfa-' + os.path.basename(f).rsplit('-', 1)[-1][:4]; tag = '%s_%s' % (y, os.path.splitext(os.path.basename(f))[0])
        out = os.path.join(WORK, tag)
        if os.path.exists(out): shutil.rmtree(out)
        t = time.time(); rec = {'src': f, 'year': y, 'file': os.path.basename(f), 'mb': round(os.path.getsize(f) / 1e6, 1)}
        env = dict(os.environ, RVT_CAPPED='1')                       # the job's own slice/scope is the memory cap
        try:
            cap = ['systemd-run', '--user', '--scope', '-q', '--slice=' + os.environ['RVT_SWEEP_SLICE'], '-p', 'MemoryMax=' + os.environ.get('RVT_SWEEP_MEM', '6G'), '-p', 'MemorySwapMax=0'] if os.environ.get('RVT_SWEEP_SLICE') and shutil.which('systemd-run') else []
            p = subprocess.run(cap + [sys.executable, '-c', 'import sys; sys.path.insert(0,%r); from rvtviewer.cli import main; main(sys.argv[1:])' % ROOT, 'convert', f, out],
                               capture_output=True, text=True, timeout=TIMEOUT, env=env)
            rec['status'] = 'ok' if p.returncode == 0 and os.path.exists(os.path.join(out, 'summary.json')) else ('killed' if p.returncode in (-9, 137) or (cap and p.returncode != 0 and not (p.stderr or '').strip()) else 'fail')
            rec['rc'] = p.returncode
            if rec['status'] != 'ok': rec['err'] = ((p.stdout or '')[-800:] + '\n--- stderr ---\n' + (p.stderr or '')[-2500:])
        except subprocess.TimeoutExpired as ex:
            rec['status'] = 'timeout'; rec['err'] = str((ex.stdout or b'')[-600:])
        rec['secs'] = round(time.time() - t, 1)
        try:
            sm = json.load(open(os.path.join(out, 'summary.json'))); mt = json.load(open(os.path.join(out, 'meta.json')))
            rec.update({k: sm.get(k) for k in ('elements', 'tris', 'true', 'matched', 'approx', 'box')}); rec['timings'] = mt.get('timings'); rec['sheets'] = len(mt.get('sheets') or []); rec['views'] = len(mt.get('views') or [])
            ms = json.load(open(os.path.join(out, 'materials.json')))['materials']; rec['materials'] = len(ms); rec['swatches'] = sum(1 for m in ms if m.get('swatch')); rec['mat_used'] = sum(1 for m in ms if m.get('elements'))
        except Exception as ex: rec.setdefault('err', repr(ex))
        if rec['status'] == 'ok' and not os.environ.get('RVT_SWEEP_NOFUNC'):          # functional test through the real server + sheets plug-in
            try:
                ft = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'functest.py'), out, os.environ.get('RVT_SWEEP_PORT', '8962')], capture_output=True, text=True, timeout=1800)
                rec['func'] = json.loads(ft.stdout.strip().splitlines()[-1])
            except Exception as ex: rec['func'] = {'ok': False, 'checks': {}, 'error': repr(ex)[:300]}
        open(OUT, 'a').write(json.dumps(rec) + '\n'); print(rec['status'], tag, rec['secs'], flush=True)
        shutil.rmtree(out, ignore_errors=True)
    print('SWEEPDONE', flush=True)

if __name__ == '__main__':
    fs = sys.argv[1:] or sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/*/*.rvt')) + glob.glob(os.path.expanduser('~/rvt-research/corpus/*/*.rte')) + glob.glob(os.path.expanduser('~/rvt-research/samples-rfa/*.rfa')), key=lambda p: os.path.getsize(p))
    main(fs)
