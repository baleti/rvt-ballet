"""Revit oracle (gt_geom) vs viewer for the single-feature rosetta families: per file, the family instance's solid volume / area from Revit's API (Fine detail, summed over its solids)
against the viewer's converted mesh (bbox IoU + volume ratio from compare.json, mesh area / analytic area from the conversion info). usage: tools/rosetta_dev.py [stem ...]"""
import sys, os, json, glob, sqlite3, re
CACHE = os.path.expanduser('~/.cache/rvt-viewer/models'); GT = os.path.expanduser('~/rvt-research/gt_geom')
STEMS = ['2024_fam_revolution_torus_base', '2024_fam_revolution_sphere_base', '2024_fam_revolution_cone_base', '2024_fam_blend_base', '2024_fam_blend_var', '2024_fam_sweep_arc_path_base', '2024_fam_sweep_arc_path_var',
         '2026_fam_blend_base', '2026_fam_sweep_arc_path_base', '2024_fam_extrusion_arc_base', '2024_fam_voidcut_base']
def main(stems):
    print('| file | Revit volume | Revit area | volume ratio (ours / Revit) | area ratio | bbox IoU | geometry |\n|---|---|---|---|---|---|---|')
    for s in stems:
        ds = sorted(glob.glob(os.path.join(CACHE, s + '-*')), key=os.path.getmtime)
        if not ds: print('| %s | no conversion |' % s); continue
        d = ds[-1]; gt = os.path.join(GT, s + '.tsv')
        fi = None; vol = area = 0.0
        for l in open(gt, errors='ignore'):
            c = l.rstrip('\n').split('\t')
            if c[0] == 'FINST' and fi is None: fi = c[1]
        for l in open(gt, errors='ignore'):
            c = l.rstrip('\n').split('\t')
            if c[0] == 'G' and fi and c[1].startswith(fi + '.1.'):
                vol += float(c[2].split('=')[1]); area += float(c[3].split('=')[1])
        cmp = {}
        if os.path.exists(d + '/compare.json'): cmp = next((v for v in json.load(open(d + '/compare.json'))['elements'].values() if str(v.get('id')) == fi), {})
        db = sqlite3.connect(d + '/model.sqlite'); row = db.execute("select e.fid, g.info from el e left join ginfo g on g.i=e.i where e.id=?", (int(fi),)).fetchone() if fi else None
        info = json.loads(row[1]) if row and row[1] else {}
        print('| %s | %.4f | %.4f | %s | %s | %s | %s |' % (s, vol, area, cmp.get('vratio', '-'), cmp.get('aratio', '-'), cmp.get('iou', '-'), row[0] if row else '-'))
main(sys.argv[1:] or STEMS)
