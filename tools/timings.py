"""first-open timings of the reference models: cold conversion (viewer raw cache + geometry cache bypassed; the reader's own caches are used as shipped) and cache-hit page load in headless Chromium.
usage: tools/timings.py   -> screenshots/timings.json + a markdown table on stdout (run under tools/capped.sh, one model at a time)"""
import sys, os, json, time, asyncio, subprocess, hashlib, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cdp
from rvtviewer import build, reader
C = os.path.expanduser('~/rvt-research/corpus')
SET0 = [('residential-2020', '2020/20_Residential_Sample_Project'), ('facades-2026', '2026/58_Snowdon_Towers_Sample_Facades'), ('hvac-2024', '2024/42_Snowdon_Towers_Sample_HVAC'),
       ('structural-2024', '2024/43_Snowdon_Towers_Sample_Structural'), ('mep-2020', '2020/23_rme_advanced_sample_project')]
SET = [x for x in SET0 if (not os.environ.get('ONLY') or x[0] in os.environ['ONLY'].split(','))]
async def page_load(d, port):
    srv = subprocess.Popen([os.path.join(ROOT, 'rvt-viewer'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1400, 900)); await b.start()
    try:
        t = time.time(); await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 180); dt = time.time() - t
        st = await b.ev("document.querySelector('#status').innerText"); return dt, st
    finally: await b.close(); srv.terminate()
def main():
    rows = []; res = {}; port = 9300
    for name, f in SET:
        p = '%s/%s.rvt' % (C, f); out = '/tmp/rvtv-timing-' + name
        key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(p), os.path.getmtime(p), os.path.getsize(p), reader.reader_stamp())).encode()).hexdigest()
        rawf = os.path.join(reader.CACHE_DIR, 'raw-' + key + '.pkl')
        if os.path.exists(rawf): os.remove(rawf)
        t = time.time(); import shutil; shutil.rmtree(out, ignore_errors=True)
        r = subprocess.run([os.path.join(ROOT, 'rvt-viewer'), 'convert', p, out], env=dict(os.environ, RVT_NO_GEOM_CACHE='1', RVT_MEM_CAP=os.environ.get('RVT_MEM_CAP', '8G')), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   # own process (and memory cap) per model
        if r.returncode != 0 or not os.path.exists(out + '/meta.json'): rows.append('| %s | conversion failed (exit %d) |' % (name, r.returncode)); print(rows[-1], flush=True); continue
        m = json.load(open(out + '/meta.json')); tot = time.time() - t; T = m['timings']; port += 1
        dt, st = asyncio.run(page_load(out, port)); subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'cleanup_browsers.py')], stdout=subprocess.DEVNULL)
        res[name] = {'size_mb': round(os.path.getsize(p) / 1e6), 'elements': len(m['elements']), 'total_s': round(tot, 1), 'timings': T, 'cache_hit_page_s': round(dt, 2), 'status': st}
        rows.append('| %s | %d MB | %d | %.0f s | %s | %.1f s |' % (name, res[name]['size_mb'], res[name]['elements'], tot, ', '.join('%s %.0f' % (k, v) for k, v in T.items() if k != 'total'), dt)); print(rows[-1], flush=True)
    json.dump(res, open(os.path.join(ROOT, 'screenshots', 'timings.json'), 'w'), indent=1)
    print('\n| model | file | elements | cold open (reader decode + geometry) | stage seconds | cache-hit page load |\n|---|---|---|---|---|---|\n' + '\n'.join(rows))
if __name__ == '__main__': main()
