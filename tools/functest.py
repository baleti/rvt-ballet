"""functional test of one converted model through the real server (no browser): tools/functest.py MODELDIR [PORT] -> JSON line of checks on stdout.
Checks: meta (phase done, elements, levels, views, sheets), model.glb (valid glTF, triangles = summary), materials.json + swatches, inspector (/api/m/<mid>/el/<i> of a drawn element
with parameters), search, plug-ins; sheets plug-in: doc.json, first sheet SVG, first plan/section view SVG (each with a timeout)."""
import sys, os, json, time, subprocess, struct, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r: return r.status, r.read()

def main(md, port=8960):
    md = os.path.abspath(md); mid = os.path.basename(md.rstrip('/')); C = {}; base = 'http://127.0.0.1:%d' % port
    srv = subprocess.Popen([sys.executable, '-c', 'import sys; sys.path.insert(0,%r); from rvtviewer.cli import main; main(sys.argv[1:])' % ROOT, 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def chk(name, fn):
        t = time.time()
        try: v = fn(); C[name] = {'ok': bool(v[0]), 'info': v[1], 's': round(time.time() - t, 1)}
        except Exception as ex: C[name] = {'ok': False, 'info': repr(ex)[:300], 's': round(time.time() - t, 1)}
    try:
        for _ in range(100):
            try: get(base + '/api/models', 2); break
            except Exception: time.sleep(0.3)
        meta = json.loads(get(base + '/m/%s/meta.json' % mid)[1]); E = meta['elements']; sm = json.load(open(os.path.join(md, 'summary.json')))
        chk('meta', lambda: (meta.get('phase') == 'done' and len(E) > 0, {'elements': len(E), 'levels': len(meta.get('levels') or []), 'views': len(meta.get('views') or []), 'sheets': len(meta.get('sheets') or []), 'batches': len(meta.get('batches') or [])}))
        def glbc():
            b = get(base + '/m/%s/model.glb' % mid, 60)[1]; mg, ver, ln = struct.unpack('<III', b[:12]); jl = struct.unpack('<I', b[12:16])[0]; js = json.loads(b[20:20 + jl])
            tris = sum(js['accessors'][p['indices']]['count'] // 3 for m in js['meshes'] for p in m['primitives'] if p.get('mode', 4) == 4 and 'indices' in p)
            return mg == 0x46546C67 and ln == len(b) and (tris > 0 or sm.get('tris', 0) == 0), {'bytes': len(b), 'tris': tris, 'summary_tris': sm.get('tris')}
        chk('glb', glbc)
        def matc():
            M = json.loads(get(base + '/m/%s/materials.json' % mid)[1])['materials']; sw = [k for k, m in enumerate(M) if m.get('swatch')]
            if sw: get(base + '/m/%s/swatch/%d.png' % (mid, sw[0]))
            return True, {'materials': len(M), 'used': sum(1 for m in M if m.get('elements')), 'swatches': len(sw), 'textures': sum(1 for m in M if m.get('tex_img'))}
        chk('materials', matc)
        def insp():
            i = next((k for k, e in enumerate(E) if e[6] not in ('none', 'line') and not e[7]), None)
            if i is None: return len(E) > 0, 'no drawn element'
            d = json.loads(get(base + '/api/m/%s/el/%d' % (mid, i))[1]); return bool(d), {'i': i, 'keys': len(d.get('params') or d.get('parameters') or {}) if isinstance(d, dict) else 0}
        chk('inspector', insp)
        chk('search', lambda: (True, len(json.loads(get(base + '/api/m/%s/search?q=wall' % mid)[1]))))
        chk('plugins', lambda: (True, [p['name'] for p in json.loads(get(base + '/api/plugins')[1])]))
        def sheets():
            t0 = time.time()
            while True:
                d = json.loads(get(base + '/sheets/api/%s/doc.json' % mid, 600)[1])
                if 'sheets' in d or d.get('state') in ('error', 'failed') or time.time() - t0 > 900: break
                time.sleep(3)
            if 'sheets' not in d: return False, 'doc.json: %s' % json.dumps(d)[:200]
            out = {'sheets': len(d['sheets']), 'views': len(d['views'])}
            if d['sheets']: st, b = get(base + '/sheets/api/%s/sheet/%s.svg' % (mid, d['sheets'][0]['id']), 600); out['sheet_svg_kb'] = len(b) // 1024; out['sheet_ok'] = st == 200 and b'<svg' in b[:2000]
            v = next((v for v in d['views'] if v.get('kind') in ('plan', 'floorplan', 'section', 'elevation', 'ceiling')), None)
            if v: st, b = get(base + '/sheets/api/%s/view/%s.svg' % (mid, v['id']), 600); out['view_svg_kb'] = len(b) // 1024; out['view_ok'] = st == 200 and b'<svg' in b[:2000]; out['view_kind'] = v.get('kind')
            return out.get('sheet_ok', True) and out.get('view_ok', True), out
        if any('sheets' in p['name'] for p in json.loads(get(base + '/api/plugins')[1])): chk('sheets', sheets)
        else: C['sheets'] = {'ok': False, 'info': 'plug-in not mounted'}
    finally: srv.terminate()
    res = {'model': mid, 'ok': all(c['ok'] for c in C.values()), 'checks': C}; print(json.dumps(res)); return res

if __name__ == '__main__': main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8960)
