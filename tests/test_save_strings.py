"""string-value edge cases through edit -> SAVE AS -> reread: each value must either be refused (nothing written) or be read back EXACTLY, with only that parameter changed (encodings, lengths, non-BMP, controls)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
if os.environ.get('STR_FILE'): os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
RTE = os.environ.get('STR_FILE') or os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); MAT = 24
from rvtballet import server, save
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
VALS = ['x', 'a b', '  lead and trail  ', 'x' * 4096, 'Ünïcödé', '日本語テキスト', 'emoji \U0001F600 non-BMP', 'é combining', 'שלום RTL', 'tab\there', 'line\nbreak', 'cr\rlf', 'quote " and \' and \\', '<xml>&amp;</xml>', ' nbsp', '​zwsp', 'a' * 255, 'a' * 256, 'a' * 1000]
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    global MAT, PARAM
    pr = rvt_params.params(src); g = lambda x: x.get('params', x)
    if os.environ.get('STR_FILE'): MAT = next(e for e, d in pr.items() if any(v == '' and '|' not in n and n in rvt_params.PNAMES.values() for n, v in g(d).items()))
    a = g(pr[MAT]); NAMES = set(rvt_params.PNAMES.values())
    if os.environ.get('STR_FILE'):      # first (element, empty string parameter) the backend accepts as stored AString
        async with TestClient(TestServer(server.make_app(models))) as c0:
            await c0.get('/api/m/m/saveinfo'); done = False
            for e, d in pr.items():
                for n, v in g(d).items():
                    if v == '' and '|' not in n and n in NAMES and (await c0.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'value': 'probe', 'param': n})).status == 200:
                        MAT = e; PARAM = n; done = True; await c0.post('/api/m/m/edit/undo'); break
                if done: break
        a = g(pr[MAT])
    name = PARAM if os.environ.get('STR_FILE') else next(n for n, v in a.items() if v == '' and '|' not in n); out = {}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for i, v in enumerate(VALS):
            r = await c.post('/api/m/m/edit', json=({'op': 'set_string', 'eid': MAT, 'value': v, 'param': name} if os.environ.get('STR_FILE') else {'op': 'set_string', 'eid': MAT, 'value': v, 'match': ''})); j = await r.json()
            if r.status != 200: out[i] = 'edit_refused:' + str(j.get('error'))[:70]; continue
            d = os.path.join(_T, 'o%d.rvt' % i); r = await c.post('/api/m/m/saveas', json={'dest': d}); j = await r.json()
            if r.status != 200: out[i] = 'save_refused:%s' % j.get('code'); assert not os.path.exists(d), i
            else:
                po = rvt_params.params(d); b = g(po[MAT]); ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
                assert ch == {name} and b[name] == v, (i, repr(v)[:30], ch, repr(b.get(name))[:40]); assert all(g(po[e]) == g(pr[e]) for e in pr if e != MAT), i; out[i] = 'ok'; os.remove(d)
            await c.post('/api/m/m/edit/undo'); assert sha(src) == h0
    print(out); assert 'ok' in out.values(); print('save strings OK', sum(x == 'ok' for x in out.values()), 'of', len(VALS))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
