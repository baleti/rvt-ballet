"""(RB_LINKTARGET=path puts the link target file beside each host) readback.py YEAR IDS FILE...: open each file in the Revit VM (audit on) and print element location / group / Mark after Regenerate"""
import sys,os
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year=int(sys.argv[1]); ids=sys.argv[2]
with guest.vmlock():
    TGT=os.environ.get('RB_LINKTARGET')
    for i,f in enumerate(sys.argv[3:]):
        port=guest.fresh(year)
        if not port: print(f,'no Revit port'); continue
        base='rb%d_%s'%(i,os.path.basename(f)); guest.put(f,'C:/wl/'+base)
        if TGT: guest.put(TGT,'C:/wl/'+os.path.basename(TGT))      # relative link target beside the host
        cs=open(os.path.expanduser('~/src/rvt-viewer/tools/rvtsave_readback.cs')).read().replace('__FILE__','C:/wl/'+base).replace('__IDS__',ids).replace('__PARAMS__',os.environ.get('RB_PARAMS',''))
        out=guest.run_job(year,port,cs,'rb%d'%i,300)
        print('==',os.path.basename(os.path.dirname(f)) or f, flush=True); L = out.replace('\r','').splitlines(); print('\n'.join(sorted(set(l for l in L if l.startswith('FAILURE')))[:5] + [l for l in L if l.startswith(('PRM','RB','REGEN','RESULT','GROUP','LINK','GI','HOST','TAG','DIM'))])[:3000], flush=True)
        guest.down(year)
