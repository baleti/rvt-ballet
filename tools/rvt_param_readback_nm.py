"""PARAM readback: YEAR "id|ParameterName,id|ParameterName" FILE...: open each file in the Revit VM (audit on) and print the stored value of each parameter through the Revit API (copy of rvtsave_readback.py)"""
import sys,os
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year=int(sys.argv[1]); ids=sys.argv[2]
with guest.vmlock():
    for i,f in enumerate(sys.argv[3:]):
        port=guest.fresh(year)
        if not port: print(f,'no Revit port'); continue
        base='rb%d_%s'%(i,os.path.basename(f)); guest.put(f,'C:/wl/'+base)
        cs=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'rvt_param_readback_nm.cs')).read().replace('__FILE__','C:/wl/'+base).replace('__IDS__',ids)
        out=guest.run_job(year,port,cs,'rb%d'%i,300)
        print('==',os.path.basename(os.path.dirname(f)) or f, flush=True); print('\n'.join(l for l in out.replace('\r','').splitlines() if l.startswith(('RB','REGEN','RESULT')))[:400000], flush=True)      # a long string value prints 5 chars per UTF-16 unit: 1500 truncated a 500-char value and hid the next elements ("not read")
        guest.down(year)
