#!/usr/bin/env python3
"""hostile_comments_rvt.py SRC OUTDIR : per hostile Comments value (CJK, emoji, umlaut, 5000 chars, newline, tab, quotes/backslash/XML, NUL, lone surrogate, empty) one fresh copy of SRC, set_string + in-place SAVE! through the app server. Prints saved/refused per value; a SAVED output must read the value back identically (or the gate must have refused) and is kept in OUTDIR for a Revit VM open (tools/rvt_vm_open.py). Exit 1 on a readback mismatch or an original changed after refusal."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
VALS = {'cjk': '\u4e2d\u6587\u6d4b\u8bd5', 'emoji': 'a\U0001F600b', 'umlaut': '\u00c4\u00d6\u00dc\u00df', 'long5000': 'x' * 5000, 'newline': 'a\nb', 'tab': 'a\tb', 'xml': '<a href="x">&amp;\'\\</a>', 'nul': 'a\x00b', 'surrogate': 'a\ud800b', 'empty': '', 'spaces': '  lead and trail  '}
async def main(src0, outdir):
    ext = os.path.splitext(src0)[1]; os.makedirs(outdir, exist_ok=True); bad = 0
    els = [e for e, d in rvt_params.params(src0).items() if g(d).get('Comments') == '']; eid = els[0]
    for name, val in VALS.items():
        work = _T + '/w_' + name + ext; shutil.copy(src0, work); orig = open(work, 'rb').read()
        md = '%s/m_%s' % (_T, name); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
        try:
            async with TestClient(TestServer(server.make_app(models))) as c:
                c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val}); es = r.status
                if es != 200: res = 'REFUSED-EDIT %s' % es; ok = open(work, 'rb').read() == orig
                else:
                    r = await c.post('/api/m/m/save', json={}); j = await r.json()
                    if r.status == 200:
                        got = g(rvt_params.params(work)[eid]).get('Comments'); ok = got == val; res = 'SAVED readback=%s' % ('equal' if ok else 'MISMATCH'); shutil.copy(work, '%s/%s%s' % (outdir, name, ext))
                    else: res = 'REFUSED %s %s' % (r.status, j.get('code')); ok = open(work, 'rb').read() == orig
        except Exception as e: res = 'EXC %s' % type(e).__name__; ok = open(work, 'rb').read() == orig
        print(name, res, 'OK' if ok else 'BAD', flush=True); bad += not ok
    sys.exit(1 if bad else 0)
asyncio.run(main(sys.argv[1], sys.argv[2]))
