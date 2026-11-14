"""rvt_query_oracle.py YEAR OUTDIR FILE...: open each file in the offline Revit VM (FilteredElementCollector over all elements and types) and write a
tab-separated oracle for fastquery.collect to OUTDIR/<basename>.oracle.tsv: E id class category_id category_name name type_id level_id owner_view_id is_type;
V id view_type is_template gen_level_id name; S id sheet_number name issue_date current_revision placed_view_ids; W id wall_type_name. Autodesk samples only."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
with guest.vmlock():
    for i, f in enumerate(sys.argv[3:]):
        port = guest.fresh(year)
        if not port: print(f, 'no Revit port', flush=True); continue
        base = 'qo%d_%s' % (i, os.path.basename(f)); guest.put(f, 'C:/wl/' + base)
        cs = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_query_oracle.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUTNAME__', 'qo%d_%d' % (i, os.getpid()))
        out = guest.run_job(year, port, cs, 'qo%d' % i, 1200)
        print('==', f, flush=True); print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('COUNT', 'RESULT'))), flush=True)
        print('pulled', guest.get('C:/wl/out/qo%d_%d.txt' % (i, os.getpid()), os.path.join(outdir, os.path.basename(f) + '.oracle.tsv'), 600), flush=True)
        guest.down(year)
