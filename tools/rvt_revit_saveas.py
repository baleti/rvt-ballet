"""rvt_revit_saveas.py YEAR OUTDIR FILE...: open each FILE in the offline Revit VM, SaveAs with the real Revit API and copy the Revit-written file to OUTDIR (files Revit itself wrote: a false-positive check for the gate that samples alone cannot give). Retries 'no Revit port' up to 5 times."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); outd = sys.argv[2]; os.makedirs(outd, exist_ok=True)
with guest.vmlock():
    for i, f in enumerate(sys.argv[3:]):
        base = 'rs%d_%s' % (i, os.path.basename(f)); ok = False
        for att in range(5):
            port = guest.fresh(year)
            if not port: print('no Revit port, attempt', att + 1, flush=True); continue
            guest.put(f, 'C:/wl/' + base)
            cs = open(os.path.expanduser('~/src/rvt-ballet/tools/rvt_revit_saveas.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUT__', 'C:/wl/out_' + base)
            out = guest.run_job(year, port, cs, 'rsave%d' % i, 300)
            print(base, [l for l in out.replace('\r', '').splitlines() if l.startswith('RESULT')][:1], flush=True)
            if 'RESULT ok' in out:
                ok = bool(guest.get('C:/wl/out_' + base, os.path.join(outd, 'revit_saved_%d_%s' % (year, os.path.basename(f))), timeout=900)); print('copy-out', 'ok' if ok else 'FAILED (file not copied)', flush=True)
            guest.down(year); break
