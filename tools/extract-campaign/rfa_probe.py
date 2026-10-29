#!/usr/bin/env python3
"""rfa_probe.py LIST.tsv OUT.jsonl : per-file parse of .rfa with the rvt-extract/reader stack (each file in its own subprocess, 5 GB address-space cap, 300 s timeout).
LIST.tsv lines: SIZE<TAB>PATH. Needs $RVT_EXTRACT and $RVT_RESEARCH on the path. Resumable (done paths are skipped)."""
import sys, os, json, time, subprocess, re
if len(sys.argv) > 2 and sys.argv[1] == '--one':
    [sys.path.insert(0, p) for p in (os.environ.get('RVT_EXTRACT'), os.environ.get('RVT_RESEARCH')) if p]
    import resource, collections
    path = sys.argv[2]; R = {}
    t0 = time.time()
    try:
        import olefile
        o = olefile.OleFileIO(path)
        bfi = o.openstream('BasicFileInfo').read().decode('utf-16le', 'ignore')
        m = re.search(r'(?<!\d)(20[12]\d)(?!\d)', bfi); R['ver'] = m.group(1) if m else None
        R['ole_streams'] = len(o.listdir())
        R['has_partatom'] = o.exists('PartAtom')
        o.close()
    except Exception as e:
        R['ole_error'] = '%s: %s' % (type(e).__name__, str(e)[:150])
    try:
        from rvtx import core
        p = core.Project(path)
        R['sec_load'] = round(time.time() - t0, 2)
        R['recs'] = len(p.recs); R['W'] = p.W
        R['incomplete'] = sum(1 for r in p.recs.values() if not r.get('complete'))
        R['rec_err'] = sum(1 for r in p.recs.values() if r.get('error'))
        real = [(k, r) for k, r in p.recs.items() if r.get('error') and k[0] != 0]
        R['rec_err_real'] = len(real)
        R['err_real_classes'] = sorted({k[1] + ': ' + str(r['error'])[:60] for k, r in real})[:6]
        try:
            from rvtx import manifest
            fs = p.families(); R['n_family_recs'] = len(fs)
            ents = [manifest.family_entry(p, f, None) for f in fs]
            e = ents[0] if ents else {}
            R['category'] = e.get('category'); R['category_id'] = e.get('category_id')
            R['types'] = len(e.get('types') or []); R['parameters'] = e.get('parameters'); R['is_2d'] = e.get('is_2d')
            R['cat_unknown'] = any(str(x.get('category')).startswith('Unknown') for x in ents)
        except BaseException as e2:
            R['manifest_error'] = '%s: %s' % (type(e2).__name__, str(e2)[:120])
        c = collections.Counter(r['class'] for r in p.recs.values())
        R['classes'] = len(c)
        R['unk'] = sum(n for k, n in c.items() if not k or k.startswith('?') or 'nknown' in k)
        R['fam_elems'] = c.get('Family', 0); R['symbols'] = c.get('FamilySymbol', 0)
        R['geom_nodes'] = sum(n for k, n in c.items() if k.startswith('G'))
        R['top'] = c.most_common(3)
    except BaseException as e:
        import traceback
        R['error'] = '%s: %s' % (type(e).__name__, str(e)[:200]); R['trace'] = traceback.format_exc()[-400:]
    R['sec'] = round(time.time() - t0, 2); R['maxrss_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    print('@@' + json.dumps(R)); sys.exit(0)
lst, out = sys.argv[1], sys.argv[2]
done = set()
if os.path.exists(out): done = {json.loads(l)['path'] for l in open(out)}
f = open(out, 'a')
for l in open(lst):
    size, path = l.rstrip('\n').split('\t', 1)
    rp = path
    if path in done: continue
    row = {'path': path, 'size': int(size)}
    try:
        pr = subprocess.run([sys.executable, '-I', os.path.abspath(__file__), '--one', rp], capture_output=True, text=True, errors='replace', timeout=300,
                            preexec_fn=lambda: __import__('resource').setrlimit(__import__('resource').RLIMIT_AS, (5 << 30, 5 << 30)))
        m = [x for x in pr.stdout.splitlines() if x.startswith('@@')]
        if m: row.update(json.loads(m[-1][2:]))
        else: row['error'] = 'crash rc=%s %s' % (pr.returncode, pr.stderr[-200:])
    except subprocess.TimeoutExpired: row['error'] = 'timeout300'
    f.write(json.dumps(row) + '\n'); f.flush()
