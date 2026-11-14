"""rvt_category_readback.py YEAR OUTDIR FILE...: open each file in the offline Revit VM and write 'CAT <id> <class> <category id or none> <category name>' for EVERY element and type to OUTDIR/<n>.txt (the oracle for rvtballet.categories); set CAT_ENUM=1 to also dump 'BIC <int> <name>' of the BuiltInCategory enum. c9x-rvtcat. Ids stay local."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
with guest.vmlock():
    for i, f in enumerate(sys.argv[3:]):
        port = guest.fresh(year)
        if not port: print(f, 'no Revit port'); continue
        base = 'cr%d_%s' % (i, os.path.basename(f)); guest.put(f, 'C:/wl/' + base)
        cs = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_category_readback.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUTNAME__', 'cr%d_%d' % (i, os.getpid())).replace('__ENUM__', os.environ.get('CAT_ENUM', '0'))
        out = guest.run_job(year, port, cs, 'cr%d' % i, 900)
        print('==', f, flush=True); print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('COUNT', 'RESULT'))), flush=True)
        print('pulled', guest.get('C:/wl/out/cr%d_%d.txt' % (i, os.getpid()), os.path.join(outdir, '%d.txt' % i), 600), flush=True)
        guest.down(year)
