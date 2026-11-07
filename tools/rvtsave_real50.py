#!/usr/bin/env python3
"""rvtsave_real50.py MANIFEST.tsv SELECTION OUTDIR [--ops mark,move] [--only fNN,...] [--maxmb N]
In-place SAVE! round trip on PRIVATE COPIES of a selection of real project files (local only). MANIFEST.tsv: id<TAB>year<TAB>bytes<TAB>path; SELECTION: comma list of ids.
Files are reported ONLY as f01..f50 (selection order). Per file and op: opens? edit status, save status/code, only the target element differs, backup == original,
original untouched. One JSON line per (file, op) appended to OUTDIR/rows.jsonl (resumable: finished pairs are skipped). Never writes to the originals.
Aggregates: tools/rvtsave_real50.py --agg OUTDIR"""
import re, os, sys, json, asyncio, tempfile, shutil, hashlib, time, argparse, collections
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path[:0] = [HERE, os.path.expanduser('~/src/savegate')]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()


def agg(out):
    rows = [json.loads(l) for l in open(os.path.join(out, 'rows.jsonl'))]
    for op in sorted({r['op'] for r in rows}):
        rs = [r for r in rows if r['op'] == op]; c = collections.Counter(r['outcome'] for r in rs)
        print('%s: files %d | %s' % (op, len(rs), ', '.join('%s %d' % kv for kv in sorted(c.items()))))
        by = collections.Counter((r['year'], r['outcome']) for r in rs)
        print('  by year: ' + '; '.join('%s %s %d' % (y, o, n) for (y, o), n in sorted(by.items(), key=str)))
    bad = [r for r in rows if r['outcome'] in ('FAIL_not_only_target', 'FAIL_original_changed', 'FAIL_backup_differs', 'ERROR')]
    print('SEV-1 / errors: %d' % len(bad)); [print('  ', r['fid'], r['op'], r['outcome'], r.get('detail', '')[:160]) for r in bad]


async def one(src_orig, year, fid, op, work):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    os.environ.update(SAVEGATE_JOURNAL=work + '/j', SAVEGATE_CACHE=work + '/c', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_SNAPSHOT_CACHE='0', RVTBALLET_EDIT_BACKEND='rvtedit')
    json.dump({'rvt': {y: 'open' for y in ('2024', '2025', '2026')}}, open(work + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = work + '/gate.json'
    from rvtballet import save, server
    src = work + '/p.rvt'; shutil.copy(src_orig, src); h0 = sha(src); t0 = time.time(); row = {'fid': fid, 'op': op, 'year': year, 'mb': round(os.path.getsize(src) / 1e6)}
    models = server.Models(); md = work + '/m'; os.makedirs(md, exist_ok=True); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        si = await (await c.get('/api/m/m/saveinfo')).json()
        if not si.get('open'):
            row.update(outcome='refused_open', detail=str(si.get('error') or ('version %s' % si.get('version')))[:160]); return row
        if si.get('workshared'): row.update(outcome='refused_workshared'); return row
        pr = save._read_params(open(src, 'rb').read())
        if op in ('mark', 'comments'):
            PAR = 'Mark' if op == 'mark' else 'Comments'
            cands = [(e, v['params'][PAR]) for e, v in sorted(pr.items()) if isinstance(v.get('params', {}).get(PAR), str) and v['params'][PAR]]
            if not cands: row.update(outcome='no_candidate'); return row
            for e, old in cands[:40]:
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': PAR, 'value': old + 'x' if len(old) < 4000 else 'x', 'match': old})
                if r.status == 200: break
            else: row.update(outcome='edit_refused', detail=(await r.text())[:160]); return row
        else:
            cands = [e for e, v in sorted(pr.items()) if v['class'] == 'FamilyInstance']
            if not cands: row.update(outcome='no_candidate'); return row
            for e in cands[:40]:
                r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 2.0}); 
                if r.status == 200: break
            else: row.update(outcome='edit_refused', detail=(await r.text())[:160]); return row
        row['eid'] = e; r = await c.post('/api/m/m/save', json={}); j = await r.json()
        if r.status != 200: row.update(outcome='save_refused_' + str(j.get('code')), detail=str(j.get('error'))[:200], original_untouched=sha(src) == h0); 
        else:
            pr2 = save._read_params(open(src, 'rb').read()); diff = [x for x in pr if pr[x] != pr2.get(x)]
            bk = j.get('backup'); row['backup_equal'] = bool(bk and os.path.exists(bk) and sha(bk) == h0); row['n_diff'] = len(diff); row['unexpected'] = (j.get('verify') or {}).get('n_unexpected')
            if os.environ.get('R50_KEEP'): os.makedirs(os.environ['R50_KEEP'], exist_ok=True); shutil.copy(src, os.path.join(os.environ['R50_KEEP'], '%s_%s.rvt' % (fid, op))); shutil.copy(src_orig, os.path.join(os.environ['R50_KEEP'], '%s_ctl.rvt' % fid)) if not os.path.exists(os.path.join(os.environ['R50_KEEP'], '%s_ctl.rvt' % fid)) else None; row['eid'] = e
            row['outcome'] = 'saved_ok' if (op == 'move' or diff == [e]) and row['backup_equal'] and not row['unexpected'] else ('FAIL_backup_differs' if not row['backup_equal'] else 'FAIL_not_only_target')
        if r.status != 200 and sha(src) != h0: row['outcome'] = 'FAIL_original_changed'
    row['s'] = round(time.time() - t0); return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('args', nargs='*'); ap.add_argument('--agg'); ap.add_argument('--ops', default='mark,move'); ap.add_argument('--only', default=''); ap.add_argument('--maxmb', type=float, default=200)
    a = ap.parse_args()
    if a.agg: return agg(a.agg)
    man, sel, out = a.args; os.makedirs(out, exist_ok=True)
    rowsf = os.path.join(out, 'rows.jsonl'); done = set()
    if os.path.exists(rowsf): done = {(json.loads(l)['fid'], json.loads(l)['op']) for l in open(rowsf)}
    meta = {}
    for l in open(man):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 4: meta[p[0]] = (p[1], p[3])
    ids = [x for x in open(sel).read().strip().split(',') if x]
    only = {x for x in a.only.split(',') if x}
    for i, fid_src in enumerate(ids, 1):
        fid = 'f%02d' % i
        if only and fid not in only: continue
        year, path = meta.get(fid_src, (None, None))
        if not path or not os.path.exists(path): continue
        if os.path.getsize(path) > a.maxmb * 1e6: 
            for op in a.ops.split(','):
                if (fid, op) not in done: open(rowsf, 'a').write(json.dumps({'fid': fid, 'op': op, 'year': year, 'mb': round(os.path.getsize(path) / 1e6), 'outcome': 'skipped_big'}) + '\n')
            continue
        for op in a.ops.split(','):
            if (fid, op) in done: continue
            work = tempfile.mkdtemp(prefix='r50-', dir=os.environ.get('R50_TMP') or out)
            try: row = asyncio.run(one(path, year, fid, op, work))
            except Exception as ex: row = {'fid': fid, 'op': op, 'year': year, 'outcome': 'ERROR', 'detail': (type(ex).__name__ + ': ' + re.sub(r'(/[^\s\'"]+)+', '<path>', str(ex)))[:160]}
            finally: shutil.rmtree(work, ignore_errors=True)
            open(rowsf, 'a').write(json.dumps(row) + '\n'); print(fid, op, row['outcome'], flush=True)


if __name__ == '__main__': main()
