"""lowmem_cmp.py PROJECT.rvt OUTDIR : rvt-extract families with and without --low-memory: peak RSS, seconds, byte-identical .rfa count. needs $RVT_EXTRACT"""
import sys,subprocess,resource,os,hashlib,time
path=sys.argv[1]; out=sys.argv[2]
res={}
for mode in ('full','low'):
    d=os.path.join(out,mode); t=time.time()
    before=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    cmd=[sys.executable,os.path.join(os.environ['RVT_EXTRACT'], 'bin', 'rvt-extract'),path,'--out',d,'--only','families']+(['--low-memory'] if mode=='low' else [])
    subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    ru=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    res[mode]=(ru//1024,round(time.time()-t))
    print(mode,'maxrss_mb(cumulative max)',ru//1024,'sec',round(time.time()-t),flush=True)
def digest(d):
    h={}
    for r,_,fs in os.walk(os.path.join(d,'families')):
        for f in fs:
            if f.endswith('.rfa'): h[os.path.relpath(os.path.join(r,f),d)]=hashlib.sha1(open(os.path.join(r,f),'rb').read()).hexdigest()
    return h
a,b=digest(os.path.join(out,'full')),digest(os.path.join(out,'low'))
print('rfa full',len(a),'low',len(b),'identical',sum(1 for k in a if b.get(k)==a[k]))
