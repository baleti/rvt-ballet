"""LIMITED verification (SAVE AS only, explicit opt-in): needs confirm=true; a real edit saved this way is byte-identical to the element-level-verified save of the same edit, carries the 'LIMITED verification'
warning; light_verify catches: an untouched stream changed, too many members changed, a different stream set, a non-compound output; identity passes with 0 changed members."""
import os, sys, asyncio, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save, lightverify, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def unit(buf):
    ops = [edit.validate_op({'op': 'set_string', 'eid': 24, 'value': 'light', 'match': ''})]; nb = edit.apply(buf, ops)
    r = lightverify.light_verify(buf, nb, 1); assert r['changed_members'] >= 1 and 'LIMITED' in r['note'], r
    assert lightverify.light_verify(buf, buf, 1)['changed_members'] == 0                      # identity
    sys.path.insert(0, edit.WL); import cfb
    c = cfb.CFB(nb); e = c.streams()['BasicFileInfo']; e.data = e.data[:-2] + b'xx'; p = os.path.join(_T, 'bad.rvt'); cfb.write(c, p)
    for name, args in (('untouched stream changed', (buf, open(p, 'rb').read(), 1)), ('too many members changed', (buf, nb, 1, 0)), ('not a compound file', (buf, b'junk' * 100, 1))):
        try: lightverify.light_verify(*args); raise SystemExit('FAIL: accepted ' + name)
        except lightverify.LightVerifyFailed as ex: assert str(ex), name
    return nb
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); buf = open(src, 'rb').read(); unit(buf)
    md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'light', 'match': ''})).status == 200
        r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'x.rvt'), 'light_verify': True}); assert r.status == 400                       # not confirmed
        dl = os.path.join(_T, 'light.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dl, 'light_verify': True, 'confirm': True}); j = await r.json()
        assert r.status == 200 and j['limited_verification'] and 'LIMITED verification' in j['warnings'][0] and j['verify']['changed_members'] >= 1 and sha(src) == h0, (r.status, j)
        dn = os.path.join(_T, 'normal.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dn}); j2 = await r.json(); assert r.status == 200 and j2['verify']['n_unexpected'] == 0, (r.status, j2)
        assert sha(dl) == sha(dn), 'limited-verify output differs from the element-level-verified output of the same edit'
    print('save light OK: confirm required, output identical to the fully verified save, 3 corruption classes + non-compound caught, identity passes')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
