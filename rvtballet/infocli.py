"""rvt-ballet info | sheets | views | levels | grids | counts | elements FILE [--json] [--refresh]: administrative data of a .rvt WITHOUT conversion.
Streamed (fastinfo.py), never starts the geometry pipeline, runs under a hard memory cap (RVT_INFO_MEM_GB, default 0.9) and caches its result per file
(path, size, mtime) so the next subcommand is instant. `info` alone never touches the partitions (BasicFileInfo, project information, editors: about a second)."""
import os, sys, json, argparse, hashlib, time
from . import plat, reader

CMDS = ('info', 'sheets', 'views', 'levels', 'grids', 'counts', 'elements')
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
    ap = argparse.ArgumentParser(prog='rvt-ballet'); ap.add_argument('cmd', choices=CMDS); ap.add_argument('file')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--refresh', action='store_true', help='ignore the cached result')
    ap.add_argument('--views', action='store_true'); ap.add_argument('--levels', action='store_true'); ap.add_argument('--grids', action='store_true')
    ap.add_argument('--tsv', action='store_true', help='elements: tab separated rows'); ap.add_argument('--limit', type=int, default=0, help='elements: first N rows only')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args(argv)
    from . import cli
    bad = cli.check_input(a.file)
    if bad: print('rvt-ballet: ' + bad, file=sys.stderr); return 2
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
