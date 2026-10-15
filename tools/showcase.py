"""geometry showcase: convert (fresh, no stale caches) the rosetta single-feature files + Snowdon facade members + 2020 residential, compare with the Revit oracle (gt_geom),
take one framed headless screenshot per object into screenshots/showcase/<name>.png (git-excluded: samples are proprietary) and write docs/SHOWCASE.md (which file shows which surface type).
usage: tools/showcase.py [name ...]     (one conversion at a time; headless Chromium, no window)"""
import asyncio, sys, os, json, subprocess, time, sqlite3, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cdp
from rvtviewer import cli
R = os.path.expanduser('~/rvt-research/rosetta'); C = os.path.expanduser('~/rvt-research/corpus')
# name, file, what to look at, optional element id to isolate+frame
SHOW = [
    ('sphere', R + '/2024_fam_revolution_sphere_base.rte', 'revolved sphere family: Revit stores no graphics for it, so it is a BOX (known reader gap)', None),
    ('torus', R + '/2024_fam_revolution_torus_base.rte', 'torus: revolution + torus surfaces, B-rep faces', None),
    ('cone', R + '/2024_fam_revolution_cone_base.rte', 'cone: cone / revolution surfaces', None),
    ('extrusion-arc', R + '/2024_fam_extrusion_arc_base.rte', 'extrusion with arc profile: cylinder faces', None),
    ('voidcut', R + '/2024_fam_voidcut_base.rte', 'family with a void cut (real cut body)', None),
    ('sketch-spline-profile', R + '/2024_fam_sketch_profile_spline_base.rte', 'sketched profile with spline edges: B-spline / ruled faces', None),
    ('blend', R + '/2024_fam_blend_base.rte', 'blend (loft between two profiles): ruled / planar faces', None),
    ('blend-var', R + '/2024_fam_blend_var.rte', 'blend, changed parameters', None),
    ('sweep-arc-path', R + '/2024_fam_sweep_arc_path_base.rte', 'sweep of a profile along an arc path (torus / swept faces)', None),
    ('sweep-arc-path-var', R + '/2024_fam_sweep_arc_path_var.rte', 'sweep along arc path, changed parameters', None),
    ('blend-2026', R + '/2026_fam_blend_base.rte', 'blend, Revit 2026 file', None),
    ('sweep-arc-path-2026', R + '/2026_fam_sweep_arc_path_base.rte', 'sweep along arc path, Revit 2026 file', None),
    ('cone-var', R + '/2024_fam_revolution_cone_var.rte', 'cone, changed parameters', None),
    ('torus-var', R + '/2024_fam_revolution_torus_var.rte', 'torus, changed parameters', None),
    ('sphere-var', R + '/2024_fam_revolution_sphere_var.rte', 'sphere, changed parameters', None),
    ('stair-run', R + '/2024_stair_run_base.rte', 'stair run (sawtooth solid) + supports + railing', None),
    ('railing', R + '/2024_railing_base.rte', 'railing: top rail, balusters, rods', None),
    ('railing-handrail-profile', R + '/2024_prof_railing_handrail_base.rte', 'handrail with a profile family', None),
    ('curtain-mullion', R + '/2024_prof_curtain_mullion_base.rte', 'curtain wall: grid lines, mullions with profile, panels', None),
    ('structural-framing-profile', R + '/2024_prof_structural_framing_base.rte', 'structural framing with a profile family', None),
    ('wall-sweep-reveal', R + '/2024_prof_wall_sweep_reveal_base.rte', 'wall sweep and reveal', None),
    ('topography', R + '/2024_topography_base.rte', 'topography TIN mesh', None),
    ('wall-curved', R + '/2024_wall_curved_base.rte', 'curved wall: cylinder faces', None),
    ('wall-profile', R + '/2024_wall_profile_base.rte', 'wall with an edited profile', None),
    ('wall-types', R + '/2024_wall_types_base.rte', 'layered wall types + curtain wall', None),
    ('wall-window', R + '/2024_wall_win2_base.rte', 'wall with a window opening (real cut)', None),
    ('house', R + '/2024_house_base.rte', 'small house: walls with openings, doors, windows, floor, room', None),
    ('facade-members', C + '/2026/58_Snowdon_Towers_Sample_Facades.rvt', 'Snowdon facade 15x25 members with ruled faces (element 609003 isolated)', 609003),
    ('residential-2020', C + '/2020/20_Residential_Sample_Project.rvt', 'Revit 2020 residential sample project', None),
]


async def shoot(d, port, out, eid):
    srv = subprocess.Popen([os.path.join(ROOT, 'rvt-viewer'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1400, 900)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 180); await asyncio.sleep(0.5)
        if eid is not None:
            await b.ev("(async()=>{const i=S.meta.elements.findIndex(r=>r[0]===%d); if(i>=0){setIsolate(new Set([i])); await zoomTo([i]);} return i})()" % eid); await asyncio.sleep(1.0)
        else: await b.ev("fitAll(new THREE.Vector3(1,0.7,1)); 0"); await asyncio.sleep(1.0)
        await b.shot(out)
    finally: await b.close(); srv.terminate()


def surfaces(d):
    c = collections.Counter(); fid = collections.Counter()
    try:
        db = sqlite3.connect(d + '/model.sqlite')
        for (info,) in db.execute('select info from ginfo'):
            for k, n in (json.loads(info).get('surfaces') or {}).items(): c[k.replace(' (OpenCascade)', '')] += n
    except Exception: pass
    m = json.load(open(d + '/meta.json')); hid = set(m.get('defaultHidden') or [])
    for cat, v in m['coverage'].items():
        if cat in hid: continue
        for k, n in v.items(): fid[k] += n
    return c, fid


def main():
    names = sys.argv[1:]; out_dir = os.path.join(ROOT, 'screenshots', 'showcase'); os.makedirs(out_dir, exist_ok=True); rows = []; port = 9100
    for name, f, what, eid in SHOW:
        if names and name not in names: continue
        t = time.time()
        try: d = cli.ensure(f, True, log=lambda *a: None)             # rebuild=True: fresh conversion
        except BaseException as ex: rows.append((name, f, what, 'conversion failed %r' % ex, '', '')); print(rows[-1], flush=True); continue
        port += 1
        try: asyncio.run(shoot(d, port, os.path.join(out_dir, name + '.png'), eid))
        except BaseException as ex: print('screenshot failed', name, repr(ex)[:100], flush=True)
        c, fid = surfaces(d)
        rows.append((name, os.path.relpath(f, os.path.expanduser('~')), what, ', '.join('%s %d' % kv for kv in fid.most_common()), ', '.join('%s %d' % kv for kv in c.most_common()), '%.0fs' % (time.time() - t)))
        print(rows[-1], flush=True)
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'cleanup_browsers.py')], stdout=subprocess.DEVNULL)
    if not names:
        with open(os.path.join(ROOT, 'docs', 'SHOWCASE.md'), 'w') as fh:
            fh.write('# Geometry showcase (which file shows which surface type)\n\nGenerated by tools/showcase.py (fresh conversions, headless screenshots in screenshots/showcase/, not committed: proprietary samples). Open a file with `./rvt-viewer open <path>`; the inspector badge lists the surface types per body.\n\n')
            fh.write('| name | file | what to look at | fidelity buckets (elements) | surface types (triangles) | time |\n|---|---|---|---|---|---|\n')
            for r in rows: fh.write('| %s | %s | %s | %s | %s | %s |\n' % r)


if __name__ == '__main__': main()
