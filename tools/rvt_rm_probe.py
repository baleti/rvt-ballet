"""rvt_rm_probe.py YEAR FILE: open FILE in the offline Revit VM and, while Revit has it open, ask the Windows Restart Manager (RmGetList) who holds the file (validates the call sequence of rvtballet/openelsewhere._win_rm). Retries 'no Revit port' up to 5 times."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year = int(sys.argv[1]); f = sys.argv[2]
with guest.vmlock():
    for att in range(5):
        port = guest.fresh(year)
        if not port: print('no Revit port, attempt', att + 1, flush=True); continue
        base = 'rm_' + os.path.basename(f); guest.put(f, 'C:/wl/' + base)
        cs = open(os.path.expanduser('~/src/rvt-ballet/tools/rvt_rm_probe.cs')).read().replace('__FILE__', 'C:/wl/' + base)
        out = guest.run_job(year, port, cs, 'rmprobe', 300)
        print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('RM', 'RESULT'))), flush=True)
        guest.down(year); break
