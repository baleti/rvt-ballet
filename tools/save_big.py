import os,sys,time,tempfile,resource,hashlib
T=os.environ.get('BIG_DIR') or tempfile.mkdtemp(); os.makedirs(T,exist_ok=True)
os.environ['SAVEGATE_JOURNAL']=T+'/j'; os.environ['SAVEGATE_CACHE']=T+'/c'
sys.path.insert(0,'~/src/rvt-viewer'); sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab'))
import cfb
src0=os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); big=T+'/big.rvt'
if not os.path.exists(big):
    c=cfb.CFB(open(src0,'rb').read()); e=[x for x in c.entries if x.type==2][0]
    # make the largest existing stream 300 MB bigger (container size stress; element data untouched)
    big_e=max((x for x in c.entries if x.type==2),key=lambda x:len(x.data)); print('stretch',big_e.name,len(big_e.data),flush=True)
    big_e.data=big_e.data+os.urandom(1<<20)*300
    t=time.time(); cfb.write(c,big); print('built',os.path.getsize(big)>>20,'MB',round(time.time()-t),'s',flush=True)
from rvtballet import save
ss=save.SaveSessions(); t=time.time()
try:
    ss.doc('m',big); print('open ok',round(time.time()-t,1),'s',flush=True)
    t=time.time(); r=save.save_as(ss,'m',big,T+'/out.rvt'); print('SAVEAS ok',round(time.time()-t,1),'s diffs',r['verify']['n_unexpected'],'identical',hashlib.sha256(open(big,'rb').read()).hexdigest()==hashlib.sha256(open(T+'/out.rvt','rb').read()).hexdigest(),flush=True)
except Exception as ex: print('ERR',type(ex).__name__,str(ex)[:200],flush=True)
print('PEAK_RSS_MB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>>10)
