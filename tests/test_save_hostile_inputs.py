"""Hostile .rvt inputs through the app (zero length, garbage, text, CFB magic only, truncated, zip, real file with a junk tail): save and saveas are REFUSED (4xx with a code), the source stays byte-identical, no output file appears, no crash. Synthetic, derived from the 2024 scene."""
import os,sys,asyncio,tempfile,hashlib,shutil,json
sys.path.insert(0,os.path.expanduser('~/src/rvt-ballet'))
_T=tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL']=_T+'/j'; os.environ['SAVEGATE_CACHE']=_T+'/bk'; os.environ['RVT_BALLET_CACHE']=_T+'/bc'; os.environ['RVT_CORE_CACHE']=_T+'/cc'; os.environ['RVTBALLET_EDIT_BACKEND']='rvtedit'
from rvtballet import server
sha=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()
REAL=os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); real=open(REAL,'rb').read() if os.path.exists(REAL) else b''
CASES={'zero_length':b'','garbage_4k':os.urandom(4096),'text_file':b'hello world\n'*100,'cfb_magic_only':bytes.fromhex('d0cf11e0a1b11ae1')+bytes(504),
 'truncated_half':real[:len(real)//2],'truncated_header':real[:600],'zip_not_cfb':b'PK\x03\x04'+bytes(200),'real_plus_junk_tail':real+b'JUNK'*1000}
async def main():
    from aiohttp.test_utils import TestClient, TestServer
    gf=os.path.join(_T,'g.json'); json.dump({'rvt':{y:'open' for y in ('2024','2025','2026')}},open(gf,'w')); os.environ['SAVEGATE_GATE']=gf; os.environ['RVTBALLET_ALLOW_OVERWRITE']='1'
    for k,(name,data) in enumerate(CASES.items()):
        src=os.path.join(_T,name+'.rvt'); open(src,'wb').write(data); h0=sha(src)
        md=os.path.join(_T,'m%d'%k); os.makedirs(md); models=server.Models(); models.m['m']={'dir':md,'name':name,'src':src}
        try:
            async with TestClient(TestServer(server.make_app(models))) as c:
                i=await (await c.get('/api/m/m/saveinfo')).json()
                r=await c.post('/api/m/m/save',json={}); j=await r.json()
                r2=await c.post('/api/m/m/saveas',json={'dest':os.path.join(_T,name+'_out.rvt')}); j2=await r2.json()
            assert r.status in (409, 415, 422) and r2.status in (409, 415, 422) and sha(src) == h0 and not os.path.exists(os.path.join(_T, name + '_out.rvt')), (name, r.status, r2.status)
            print('%-20s open=%s | save %s %s | saveas %s %s | source unchanged %s | out exists %s'%(name,i.get('open'),r.status,j.get('code'),r2.status,j2.get('code'),sha(src)==h0,os.path.exists(os.path.join(_T,name+'_out.rvt'))),flush=True)
        finally: pass
if not os.path.exists(REAL): print('skipped (scene missing)'); sys.exit(0)
try: asyncio.run(main()); print('OK', len(CASES), 'cases')
finally: shutil.rmtree(_T, ignore_errors=True)
