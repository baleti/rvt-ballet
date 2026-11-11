"""rotation readback (copy of rvtsave_readback.py + LocationPoint.Rotation in degrees): open each file in the Revit VM (audit on) and print element location / group / Mark after Regenerate"""
import sys,os
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year=int(sys.argv[1]); ids=sys.argv[2]
with guest.vmlock():
    for i,f in enumerate(sys.argv[3:]):
        port=guest.fresh(year)
        if not port: print(f,'no Revit port'); continue
        base='rb%d_%s'%(i,os.path.basename(f)); guest.put(f,'C:/wl/'+base)
        cs=open(os.path.expanduser('~/.sgtmp/tools2/rvt_rotation_readback.cs')).read().replace('__FILE__','C:/wl/'+base).replace('__IDS__',ids)
        out=guest.run_job(year,port,cs,'rb%d'%i,300)
        print('==',os.path.basename(os.path.dirname(f)) or f, flush=True); print('\n'.join(l for l in out.replace('\r','').splitlines() if l.startswith(('RB','REGEN','RESULT','TF')))[:400000], flush=True)
        guest.down(year)
