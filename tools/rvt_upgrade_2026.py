"""Make a REAL Revit 2026 project from a 2024 one: open it in the Revit 2026 guest (audit on), SaveAs in the guest, fetch the result. usage: tools/rvt_upgrade_2026.py IN.rvt OUT.rvt  (research helper; the guest is shared: it waits for the VM lock; the output is a client file when IN is: keep it local)"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
src, dst = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]); year = 2026
with guest.vmlock():
    port = guest.fresh(year)
    if not port: print('no Revit port'); sys.exit(2)
    base = 'up_' + os.path.basename(src); guest.put(src, 'C:/wl/' + base)
    cs = open(os.path.expanduser('~/src/rvt-viewer/tools/rvt_upgrade_2026.cs')).read().replace('__FILE__', 'C:/wl/' + base).replace('__OUT__', 'C:/wl/out26_' + base)
    out = guest.run_job(year, port, cs, 'up0', 590)
    print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith('RESULT')))
    if 'RESULT ok' in out: guest.get('C:/wl/out26_' + base, dst); print('fetched', os.path.getsize(dst), 'bytes')
    guest.down(year)
