"""rvt_elemhash_readback.py YEAR OUTDIR FILE...: (hashes are written to a file in the guest and pulled back to OUTDIR/<n>.txt, the console transport truncates at about 10 KB) open each file in the offline Revit VM (audit on) and print 'EH <elementid> <fnv1a-32 of class|name|group|all parameter name=value|location>' for EVERY element and type, so two files can be compared element by element in Revit's own view (tools/rvt_elemhash_compare.py). c6x-rvtmatrix. Aggregate use only: ids stay local."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
with guest.vmlock():
    for i, f in enumerate(sys.argv[3:]):
        port = guest.fresh(year)
        if not port: print(f, 'no Revit port'); continue
        base = 'eh%d_%s' % (i, os.path.basename(f)); guest.put(f, 'C:/wl/' + base)
        cs = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_elemhash_readback.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUTNAME__', 'eh%d_%d' % (i, os.getpid())).replace('__IDS__', os.environ.get('EH_IDS', ''))
        out = guest.run_job(year, port, cs, 'eh%d' % i, 900)
        print('==', f, flush=True); print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('COUNT', 'RESULT'))), flush=True)
        ok = guest.get('C:/wl/out/eh%d_%d.txt' % (i, os.getpid()), os.path.join(outdir, '%d.txt' % i), 600); print('pulled', ok, flush=True)
        if os.environ.get('EH_IDS'): print('pulled ed', guest.get('C:/wl/out/eh%d_%d.ed.txt' % (i, os.getpid()), os.path.join(outdir, '%d.ed.txt' % i), 600), flush=True)
        guest.down(year)
