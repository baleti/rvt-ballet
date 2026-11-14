"""rvt_wallmat_oracle.py YEAR OUTDIR FILE...: Revit VM oracle for the benchmark "walls below 5 m with a red material in any property": W wall_id type_id unconnected_height_ft kind; T type_id kind layer_material_ids; M material_id color/cut/surface pattern colours + every appearance-asset colour (4d) / 3d property. Autodesk samples only."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
with guest.vmlock():
    for i, f in enumerate(sys.argv[3:]):
        port = guest.fresh(year)
        if not port: print(f, 'no Revit port', flush=True); continue
        base = 'wm%d_%s' % (i, os.path.basename(f)); guest.put(f, 'C:/wl/' + base)
        cs = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_wallmat_oracle.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUTNAME__', 'wm%d_%d' % (i, os.getpid()))
        out = guest.run_job(year, port, cs, 'wm%d' % i, 1200)
        print('==', f, flush=True); print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('COUNT', 'RESULT'))), flush=True)
        print('pulled', guest.get('C:/wl/out/wm%d_%d.txt' % (i, os.getpid()), os.path.join(outdir, os.path.basename(f) + '.wallmat.tsv'), 600), flush=True)
        guest.down(year)
