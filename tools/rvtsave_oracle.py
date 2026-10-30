#!/usr/bin/env python3
"""rvtsave_oracle.py SRC YEAR SCENARIO [EID]: edit + SAVE AS / in-place SAVE through rvtballet (savegate), then open the output in the offline Revit VM (audit on).
SCENARIO: none | move | param | delete | none_inplace | move_inplace.  Output: one TSV line (savegate-matrix.tsv RVT row format). Work files stay in ~/rvtsave-work (local only)."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
W = os.path.expanduser('~/rvtsave-work'); os.makedirs(W, exist_ok=True)
_T = tempfile.mkdtemp(dir=W); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def save(src, scen, eid):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    inplace = scen.endswith('_inplace'); op = scen.replace('_inplace', '')
    if inplace: os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
    md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        body = {'none': None, 'move': {'op': 'move', 'eid': eid, 'dx': 2.0}, 'param': {'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'rvtsave'}, 'delete': {'op': 'delete', 'eid': eid}}[op]
        if body:
            r = await c.post('/api/m/m/edit', json=body)
            if r.status != 200: return None, 'edit refused: %s' % (await r.text())[:150]
        if inplace: r = await c.post('/api/m/m/save', json={}); out = src
        else: out = _T + '/out' + os.path.splitext(src)[1]; r = await c.post('/api/m/m/saveas', json={'dest': out})
        j = await r.json(); return (out if r.status == 200 else None), ('ok' if r.status == 200 else 'refused: %s' % str(j.get('error'))[:200])
def pick(path):
    sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research')]
    from savegate import rvt_elements as R
    d = R.elements(open(path, 'rb').read())
    import json
    for e, v in d.items():
        if v.startswith('FamilyInstance|') and e > 1000 and json.loads(v.split('|')[1])[2]: return e
    return 0
def main(src, year, scen, eid=0):
    work = _T + '/src' + os.path.splitext(src)[1]; shutil.copy(src, work); h0 = sha(work)
    eid = int(eid) or (pick(work) if scen.replace('_inplace', '') != 'none' else 0)
    out, msg = asyncio.run(save(work, scen, eid))
    untouched = sha(work) == h0
    if out is None:
        print('\t'.join(['c3x-rvtsave', os.path.basename(src)[:8], year, scen, 'refused', 'src_untouched=%s' % untouched, msg])); return
    if os.environ.get('RVTSAVE_NOVM'):
        keep = '%s/outs/%s_%s_%s%s' % (W, os.path.basename(src)[:2], year, scen, os.path.splitext(src)[1]); os.makedirs(os.path.dirname(keep), exist_ok=True); shutil.copy(out, keep)
        print('\t'.join(['c3x-rvtsave', os.path.basename(src)[:8], year, scen, 'saved', 'eid=%s' % eid, 'gate_accepted', 'out=' + keep, 'changed_vs_src=%s' % (sha(out) != h0)])); return
    sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'
    import stages
    r = stages.api_stage(int(year), out, True, 'rs%s' % _T[-6:])
    print('\t'.join(['c3x-rvtsave', os.path.basename(src)[:8], year, scen, 'saved', 'eid=%s' % eid, 'revit_open=%s' % r['ok'], 'cmp=%s' % (r.get('cmp'),), 'dialogs=%s' % r.get('dialogs'), 'failures=%s' % r.get('failures'), (r.get('err') or '')[:100]]))
if __name__ == '__main__': main(*sys.argv[1:])
