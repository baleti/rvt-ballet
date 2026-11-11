"""rvt-ballet info | sheets | views | levels | grids | counts | elements FILE [--json] [--refresh]: administrative data of a .rvt WITHOUT conversion.
Streamed (fastinfo.py), never starts the geometry pipeline, runs under a hard memory cap (RVT_INFO_MEM_GB, default 0.9) and caches its result per file
(path, size, mtime) so the next subcommand is instant. `info` alone never touches the partitions (BasicFileInfo, project information, editors: about a second)."""
import os, sys, json, argparse, hashlib, time
from . import plat, reader

CMDS = ('info', 'sheets', 'views', 'levels', 'grids', 'counts', 'elements', 'diff')
VERSION = 'fi1'


def cache_file(path):
    st = os.stat(path)
    key = hashlib.md5(('%s|%d|%s|%s' % (os.path.abspath(path), st.st_size, st.st_mtime, VERSION)).encode()).hexdigest()[:16]
    return os.path.join(reader.CACHE_DIR, 'info-' + key + '.json')


def _scan_cached(path, refresh=False, say=lambda m: None):
    from . import fastinfo
    fn = cache_file(path)
    if not refresh and os.path.exists(fn):
        try: return json.load(open(fn))
        except Exception: pass
    r = fastinfo.scan(path, log=say, want_elements=True)
    os.makedirs(reader.CACHE_DIR, exist_ok=True)
    import numpy as np
    arr = r.pop('arrays'); nf = fn[:-5] + '.npz'; tmp = nf + '.%d.tmp.npz' % os.getpid(); np.savez_compressed(tmp, **arr); os.replace(tmp, nf)
    tmp = fn + '.%d.tmp' % os.getpid(); json.dump(r, open(tmp, 'w'), default=str); os.replace(tmp, fn)
    return r


def _elements(path):
    import numpy as np
    z = np.load(cache_file(path)[:-5] + '.npz'); return z


def _fmt_ft(v): return '' if v is None else '%.3f ft (%.3f m)' % (v, v * 0.3048)


def _capped(argv):
    """re-run this command in a memory-capped child (systemd-run scope / Job Object / RLIMIT_AS); False when already the child"""
    if os.environ.get('RVT_CAPPED') or os.environ.get('RVT_NO_CAP'): return None
    gb = float(os.environ.get('RVT_INFO_MEM_GB', '0.9'))
    code = "import sys; sys.path.insert(0,%r); from rvtballet.infocli import main; sys.exit(main(sys.argv[1:]))" % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = plat.proc.popen_capped([sys.executable, '-c', code] + list(argv), mem_gb=gb, env=dict(os.environ, RVT_CAPPED='1'))
    return p.wait()


def main(argv, say=print):
    ap = argparse.ArgumentParser(prog='rvt-ballet'); ap.add_argument('cmd', choices=CMDS); ap.add_argument('file'); ap.add_argument('file2', nargs='?'); ap.add_argument('--deep', default='', help='diff: comma list of element ids whose FULL records are decoded in both files and compared field by field'); ap.add_argument('--allow', default='', help='diff: comma list of element ids expected to change')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--refresh', action='store_true', help='ignore the cached result')
    ap.add_argument('--views', action='store_true'); ap.add_argument('--levels', action='store_true'); ap.add_argument('--grids', action='store_true')
    ap.add_argument('--tsv', action='store_true', help='elements: tab separated rows'); ap.add_argument('--limit', type=int, default=0, help='elements: first N rows only')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args(argv)
    from . import cli
    bad = cli.check_input(a.file)
    if bad: print('rvt-ballet: ' + bad, file=sys.stderr); return 2
    if a.cmd == 'diff' and (not a.file2 or cli.check_input(a.file2)): print('rvt-ballet: diff needs two readable .rvt files', file=sys.stderr); return 2
    rc = _capped(argv)
    if rc is not None: return rc
    from . import fastinfo
    path = os.path.abspath(a.file); lg = (lambda m: print(m, file=sys.stderr, flush=True)) if a.verbose else (lambda m: None)
    t0 = time.time()
    if a.cmd == 'info' and not (a.views or a.levels or a.grids):
        r = fastinfo.file_info(path)
        if a.json: say(json.dumps(r, indent=1, default=str)); return 0
        i = r['info']
        say('%s: %.1f MB, %d partitions' % (os.path.basename(path), r['file_size'] / 1e6, r['partitions']))
        say('  Revit            %s (build %s)' % (i.get('Format', '?'), i.get('Build', '?')))
        say('  Worksharing      %s' % i.get('Worksharing', '?'))
        if i.get('Central Model Path'): say('  Central path     %s' % i['Central Model Path'])
        if i.get('Username'): say('  Username         %s' % i['Username'])
        if i.get('Last Save Path'): say('  Last save path   %s' % i['Last Save Path'])
        if r.get('last_saved'): say('  Last saved       %s by %s (%d save records in the increment table, first %s)' % (r['last_saved'], r['last_saved_by'], r['save_records'], r['first_saved']))
        say('  File modified    %s' % r['mtime'])
        for k, v in r['project'].items(): say('  %-16s %s' % (k, v))
        if r['editors']: say('  Editors (increment table): %s' % ', '.join(r['editors'][:12]))
        say('  rvt-ballet sheets|views|levels|grids|counts|elements FILE for the model data (streamed, no conversion)')
        return 0
    if a.cmd == 'diff': return _diff(path, os.path.abspath(a.file2), a, say, lg)
    r = _scan_cached(path, a.refresh, lg)
    if a.cmd == 'info':
        out = {k: r[k] for k in ('levels', 'grids', 'views') if getattr(a, k)}
        say(json.dumps(out, indent=1, default=str) if a.json else '')
        if not a.json:
            if a.levels:
                for l in r['levels']: say('  Level %-30s %s' % (l['name'], _fmt_ft(l['elevation_ft'])))
            if a.grids: say('  Grids (%d): %s' % (len(r['grids']), ', '.join(r['grids'])))
            if a.views:
                for v in r['views']: say('  %s %s' % (v['class'].replace('DBView', ''), v['name']))
        return 0
    if a.cmd == 'sheets':
        if a.json: say(json.dumps(r['sheets'], indent=1, default=str)); return 0
        say('Sheets (%d):' % len(r['sheets']))
        for s in r['sheets']: say('  %-8s %s%s%s | views: %s' % (s['number'], s['name'], ('  (issued %s)' % s['issue_date']) if s.get('issue_date') else '', ('  rev %s' % s['revision']) if s.get('revision') else '', ', '.join(s['views']) or '-'))
    elif a.cmd == 'views':
        if a.json: say(json.dumps(r['views'], indent=1, default=str)); return 0
        vv = [v for v in r['views'] if not v['template']]; say('Views (%d, %d templates not listed):' % (len(vv), len(r['views']) - len(vv)))
        for v in vv: say('  %-18s %s' % (v['class'].replace('DBView', ''), v['name']))
    elif a.cmd == 'levels':
        if a.json: say(json.dumps(r['levels'], indent=1, default=str)); return 0
        for l in r['levels']: say('%-30s %s' % (l['name'], _fmt_ft(l['elevation_ft'])))
    elif a.cmd == 'grids':
        if a.json: say(json.dumps(r['grids'], indent=1, default=str)); return 0
        for g in r['grids']: say(g)
    elif a.cmd == 'counts':
        out = {'by_category': r['counts'], 'by_class': r['class_counts'], 'view_owned_elements': r['view_owned'], 'elements': r['stats']['elements_with_header']}
        if a.json: say(json.dumps(out, indent=1, sort_keys=True)); return 0     # sorted keys: diffable between saves
        say('elements with header: %d (%d owned by a view: 2D annotation/detail)' % (out['elements'], out['view_owned_elements']))
        say('by category:')
        for k, v in r['counts'].items(): say('  %8d  %s' % (v, k))
    elif a.cmd == 'elements':
        z = _elements(path); catn = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'category_names.json'))); cn = [str(x) for x in z['cls_names']]
        n = len(z['id']); n = min(n, a.limit) if a.limit else n
        def row(i):
            c = int(z['cat'][i]); b = z['bbox'][i]; k = int(z['cls'][i])
            return (int(z['id'][i]), cn[k] if k != 65535 else '', c, catn.get(str(c), ''), int(z['owner_view'][i]), int(z['family'][i]), None if b[0] != b[0] else [float(v) for v in b])
        if a.json:
            say('['); 
            for i in range(n):
                x = row(i); say(json.dumps(dict(zip(('id', 'class', 'category_id', 'category', 'owner_view', 'family', 'bbox_ft'), x))) + (',' if i + 1 < n else ''))
            say(']'); return 0
        say('id\tclass\tcategory\towner_view\tfamily\tbbox_ft(min xyz, max xyz)')
        for i in range(n):
            x = row(i); say('%s\t%s\t%s\t%s\t%s\t%s' % (x[0], x[1], x[3] or x[2], '' if x[4] == -1 else x[4], '' if x[5] == -1 else x[5], ' '.join('%.3f' % v for v in x[6]) if x[6] else ''))
    return 0


def _diff(pa, pb, a, say, lg):
    """before/after sanity at element-header level: lost / new elements, changed category / owner view / family / bbox, plus category counts, sheets, levels, views.
    Exit 0 when every difference is on an --allow id (or there is none), 1 otherwise. NOT a replacement for opening the file in Revit."""
    import numpy as np
    ra = _scan_cached(pa, a.refresh, lg); rb = _scan_cached(pb, a.refresh, lg); A = _elements(pa); B = _elements(pb)
    allow = {int(x) for x in a.allow.split(',') if x.strip()}
    ia = {int(i): k for k, i in enumerate(A['id'])}; ib = {int(i): k for k, i in enumerate(B['id'])}
    lost = sorted(set(ia) - set(ib)); new = sorted(set(ib) - set(ia)); chg = {}
    for i in set(ia) & set(ib):
        x, y = ia[i], ib[i]; what = [col for col in ('cat', 'owner_view', 'family') if A[col][x] != B[col][y]]
        if not np.array_equal(A['bbox'][x], B['bbox'][y], equal_nan=True): what.append('bbox')
        if what: chg[i] = what
    cd = {k: (ra['counts'].get(k, 0), rb['counts'].get(k, 0)) for k in set(ra['counts']) | set(rb['counts']) if ra['counts'].get(k, 0) != rb['counts'].get(k, 0)}
    lv = {l['id']: l['name'] for l in ra['levels']}, {l['id']: l['name'] for l in rb['levels']}
    out = {'lost': lost, 'new': new, 'changed': {str(k): v for k, v in sorted(chg.items())}, 'count_diffs': cd, 'sheets_equal': ra['sheets'] == rb['sheets'], 'views_equal': ra['views'] == rb['views'],
           'level_names_changed': {str(i): [lv[0].get(i), lv[1].get(i)] for i in set(lv[0]) | set(lv[1]) if lv[0].get(i) != lv[1].get(i)}}
    bad = [i for i in lost + new + list(chg) if i not in allow]
    out['unexpected'] = len(bad) + (0 if out['sheets_equal'] else 1) + (0 if out['views_equal'] else 1) + len(out['level_names_changed'])
    if a.json: say(json.dumps(out, indent=1))
    else:
        say('lost %d, new %d, changed %d (%s), unexpected %d' % (len(lost), len(new), len(chg), ', '.join('%s:%s' % (k, '+'.join(v)) for k, v in list(sorted(chg.items()))[:8]), out['unexpected']))
        say('category count diffs: %s | sheets equal %s | views equal %s | level names changed %s' % (cd or 'none', out['sheets_equal'], out['views_equal'], out['level_names_changed'] or 'none'))
    if a.deep:
        ids = [int(x) for x in a.deep.split(',') if x.strip()]; out['deep'] = _deep(pa, pb, ids); say(json.dumps(out['deep'], indent=1, default=str)) if not a.json else None
    return 1 if out['unexpected'] else 0


def _walk(x, path, out, lim=60):
    if len(out) >= lim: return
    if isinstance(x, dict): [_walk(v, path + '.' + str(k), out, lim) for k, v in x.items()]
    elif isinstance(x, (list, tuple)) and len(x) <= 64: [_walk(v, path + '[%d]' % i, out, lim) for i, v in enumerate(x)]
    else: out[path] = repr(x)[:80]


def _deep(pa, pb, ids):
    """full records of `ids` (rvt_fast.extract only_ids, fields flattened) in both files -> {id: {'class':..., 'changed': {path: [a, b]}, 'only_a': n, 'only_b': n}}"""
    from . import fastinfo; fastinfo._tune(); fastinfo._paths(); import rvt_fast as F
    R = []
    for p in (pa, pb):
        x = F.extract(p, only_ids=ids, want_all=True); d = {}
        for (eid, c), rec in x['recs'].items():
            if eid in ids and eid not in d: f = {}; _walk(rec['fields'], '', f, 100000); d[eid] = (c, f)
        R.append(d)
    res = {}
    for i in ids:
        a, b = R[0].get(i), R[1].get(i)
        if not a or not b: res[str(i)] = {'present': [bool(a), bool(b)]}; continue
        ch = {k: [a[1].get(k), b[1].get(k)] for k in set(a[1]) | set(b[1]) if a[1].get(k) != b[1].get(k)}
        res[str(i)] = {'class': a[0], 'fields_changed': len(ch), 'changed': dict(sorted(ch.items())[:40])}
    return res
