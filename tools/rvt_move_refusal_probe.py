import os, sys, asyncio, tempfile, json, shutil, collections
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVT_BALLET_CACHE=_T+'/bc', RVT_CORE_CACHE=_T+'/cc')
import atexit; atexit.register(shutil.rmtree,_T,True)
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
for p in ('~/rvt-research','~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import server
import rvt_params
WANT=('Floor','FootPrintRoof','ProfileRoof','Ceiling','RoofBase','Roof')
async def main(src):
    pr=rvt_params.params(src); by=collections.defaultdict(list)
    for e,v in pr.items():
        if v['class'] in WANT or 'Ceiling' in v['class'] or 'Roof' in v['class']: by[v['class']].append(e)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models=server.Models(); md=_T+'/m'; os.makedirs(md); cp=_T+'/copy.rvt'; shutil.copy(src,cp); models.m['m']={'dir':md,'name':'f','src':cp}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        for cls,ids in by.items():
            for e in ids[:2]:
                r=await c.post('/api/m/m/edit',json={'op':'move','eid':e,'dx':1.0,'dy':0.0,'dz':0.0}); j=await r.json()
                print(cls,e,r.status,str(j.get('error'))[:260],flush=True)
                if r.status==200: await c.post('/api/m/m/edit/undo',json={})
asyncio.run(main(sys.argv[1]))
