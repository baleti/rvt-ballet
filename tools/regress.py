"""screenshot-regression set: convert (cached) + headless screenshot of 5 reference models, fidelity percentages, pixel diff against the previous run.
usage: tools/regress.py [--rebuild]    output: screenshots/regress/<name>.png, previous run kept as <name>.prev.png, summary in screenshots/regress/summary.md (all git-excluded)"""
import asyncio, sys, os, json, subprocess, shutil, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cdp
from rvtviewer import cli
C = os.path.expanduser('~/rvt-research/corpus')
SET = [('residential-2020', '2020/20_Residential_Sample_Project'), ('structural-2024', '2024/43_Snowdon_Towers_Sample_Structural'), ('mep-2020', '2020/23_rme_advanced_sample_project'),
       ('hvac-2024', '2024/42_Snowdon_Towers_Sample_HVAC'), ('facades-2026', '2026/58_Snowdon_Towers_Sample_Facades')]
OUT = os.path.join(ROOT, 'screenshots', 'regress')

def pixdiff(a, b):
    from PIL import Image, ImageChops
    A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB')
    if A.size != B.size: return 100.0
    d = ImageChops.difference(A, B).convert('L').point(lambda v: 255 if v > 24 else 0)
    return 100.0 * sum(1 for v in d.getdata() if v) / (A.size[0] * A.size[1])

async def shoot(d, port, out):
    srv = subprocess.Popen([os.path.join(ROOT, 'rvt-viewer'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 950)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 120); await asyncio.sleep(0.5)
        await b.ev("fitAll(new THREE.Vector3(1,0.7,1)); 0"); await asyncio.sleep(1.0); await b.shot(out)
    finally: await b.close(); srv.terminate()

def main():
    os.makedirs(OUT, exist_ok=True); rebuild = '--rebuild' in sys.argv; rows = []; port = 8900
    for name, f in SET:
        p = '%s/%s.rvt' % (C, f); t = time.time()
        try: d = cli.ensure(p, rebuild, log=lambda *a: None); m = json.load(open(d + '/meta.json'))
        except BaseException as ex: rows.append('| %s | conversion failed: %s | | | | | |' % (name, repr(ex)[:60])); print(rows[-1], flush=True); continue
        cur = os.path.join(OUT, name + '.png'); prev = os.path.join(OUT, name + '.prev.png')
        if os.path.exists(cur): shutil.copy(cur, prev)
        port += 1; asyncio.run(shoot(d, port, cur))
        tot = {}; hid = set(m.get('defaultHidden') or [])
        for c, v in m['coverage'].items():
            if c in hid: continue
            for k, n in v.items(): tot[k] = tot.get(k, 0) + n
        tr, mt, ap, bx = tot.get('solid', 0) + tot.get('mesh', 0), tot.get('matched', 0), tot.get('param', 0) + tot.get('approx', 0), tot.get('bbox', 0); n = max(tr + mt + ap + bx, 1)
        diff = pixdiff(cur, prev) if os.path.exists(prev) else None
        rows.append('| %s | %d | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %s |' % (name, n, 100 * tr / n, 100 * mt / n, 100 * ap / n, 100 * bx / n, 'new' if diff is None else '%.1f%%' % diff))
        print(rows[-1], flush=True)
    open(os.path.join(OUT, 'summary.md'), 'w').write('| model | elements | true geometry (B-rep / saved mesh) | parametric, extents match | approximate | box only | pixel change vs previous |\n|---|---|---|---|---|---|---|\n' + '\n'.join(rows) + '\n')
main()
