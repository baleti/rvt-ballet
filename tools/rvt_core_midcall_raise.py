"""rvt_core_midcall_raise.py MODE (native|nofast|stub|allraise|midraise) [env F=file.rvt, run with PYTHONPATH=~/rvt-research]: rvt_entities.extract(want_all) record-count + hash. env RAISE=base raises a BaseException subclass (pyo3 PanicException stand-in), env RC_DIR sets the cache dir; midraise = RecDecoder.extract_stored raises mid-call: the hash must equal native (fallback to the Python oracle). Scratch-grade probe; use a fresh RVT_CORE_CACHE (set inside)."""
import sys,types,os,hashlib,pickle
class PanicLike(BaseException): pass
mode=sys.argv[1]; n=[0]
if mode=='midraise':
    import importlib.util
    fn=os.path.expanduser('~/rvt-research/rvt_core.abi3.so'); sp=importlib.util.spec_from_file_location('rvt_core',fn); real=importlib.util.module_from_spec(sp); sp.loader.exec_module(real)
    RR=real.RecDecoder
    class W:
        cache_header=staticmethod(getattr(RR,'cache_header',None)) if hasattr(RR,'cache_header') else None
        def __init__(s,*a,**k): s._r=RR(*a,**k)
        def __getattr__(s,k): return getattr(s._r,k)
        def extract_stored(s,*a,**k): n[0]+=1; raise (PanicLike if os.environ.get('RAISE')=='base' else RuntimeError)('injected mid-call')
    m=types.ModuleType('rvt_core')
    for k in dir(real):
        if not k.startswith('__'): setattr(m,k,getattr(real,k))
    m.RecDecoder=W; sys.modules['rvt_core']=m; mode='stubdone'
if mode=='allraise':
    import importlib.util,glob
    fn=os.path.expanduser('~/rvt-research/rvt_core.abi3.so'); sp=importlib.util.spec_from_file_location('rvt_core',fn); real=importlib.util.module_from_spec(sp); sp.loader.exec_module(real)
    m=types.ModuleType('rvt_core'); n=[0]
    def mk(nm,f):
        def w(*a,**k): n[0]+=1; raise RuntimeError('injected '+nm)
        return w
    for k in dir(real):
        if not k.startswith('__'):
            v=getattr(real,k); setattr(m,k,mk(k,v) if callable(v) and not isinstance(v,type) else v)
    sys.modules['rvt_core']=m; mode='stub'
if mode=='stub':
    m=types.ModuleType('rvt_core'); n=[0]
    class RD:
        def __init__(s,*a,**k): pass
        def set_es(s,v): pass
        def set_strcap(s,v): pass
        def record(s,*a,**k): n[0]+=1; raise RuntimeError('x')
    m.RecDecoder=RD; m.parse_formats=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('y'))
    sys.modules['rvt_core']=m
elif mode=='nofast': os.environ['RVT_NOFAST']='1'
os.environ['RVT_CORE_CACHE']=os.environ.get('RC_DIR') or '/tmp/none-rc-'+mode; os.environ['RVT_WORKERS']='1'
import rvt_entities
f=os.environ.get('F') or os.path.expanduser('~/rvt-samples/racbasicsamplefamily-2024.rfa')
try:
    r=rvt_entities.extract(f,want_all=True)
    print(mode,len(r['recs']),hashlib.sha256((repr(sorted((str(k),repr(v)) for k,v in r['recs'].items()))+repr(sorted((str(k),repr(v)) for k,v in r.get('eh',{}).items()))+repr(r.get('W'))).encode()).hexdigest()[:12], 'record calls', n[0] if 'n' in dir() else '-')
except Exception as e: print(mode,'EXC',type(e).__name__,str(e)[:100])
