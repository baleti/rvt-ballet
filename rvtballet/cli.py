"""rvt-ballet open FILE.rvt | convert FILE.rvt OUTDIR | serve [DIRS...]"""
import urllib.parse, os, sys, argparse, hashlib, json, subprocess, shutil, time
from . import reader, plat

def model_dir(path):
    key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader.reader_stamp() + reader.viewer_stamp())).encode()).hexdigest()[:12]
    return os.path.join(reader.CACHE_DIR, 'models', os.path.splitext(os.path.basename(path))[0] + '-' + key)

BUILD_VERSION = 'b3'

def check_input(path):
    """-> None when `path` looks like a readable Revit file, else a one-line human reason (no traceback in a demo)"""
    if not os.path.exists(path): return 'file not found: %s' % path
    if os.path.isdir(path): return 'this is a folder, not a .rvt/.rte/.rfa file: %s' % path
    try:
        with open(path, 'rb') as f: head = f.read(8)
    except OSError as ex: return 'cannot read %s: %s' % (path, ex.strerror)
    if os.path.getsize(path) == 0: return '%s is empty (0 bytes)' % os.path.basename(path)
    if head != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': return '%s is not a Revit file (no OLE2 header; Revit .rvt/.rte/.rfa files start with D0CF11E0A1B11AE1)' % os.path.basename(path)
    return None

def friendly_error(ex):
    """short, specific reason for a failed conversion"""
    t = '%s: %s' % (type(ex).__name__, ex)
    if 'gzip' in t or 'zlib' in t or 'Incorrect header' in t or 'truncated' in t.lower(): return 'the file looks truncated or corrupted (%s)' % t[:120]
    if 'NotOleFile' in t: return 'not a Revit file (%s)' % t[:120]
    if isinstance(ex, MemoryError): return 'out of memory while reading this file'
    return t[:200]

def best_cached(path):
    """newest COMPLETE conversion of this very file (same path, size, mtime) made with any reader/viewer version, or None. A reader or converter change must never
    turn a prepared demo into a cold conversion: the older complete model opens at once and the page offers the update."""
    root = os.path.join(reader.CACHE_DIR, 'models'); ap = os.path.abspath(path); base = os.path.splitext(os.path.basename(path))[0] + '-'
    try: sz = os.path.getsize(path); mt = os.path.getmtime(path)
    except OSError: return None
    best = None
    for n in os.listdir(root) if os.path.isdir(root) else []:
        if not n.startswith(base) or n.endswith('.tmp'): continue
        d = os.path.join(root, n)
        try:
            sm = json.load(open(os.path.join(d, 'summary.json')))
            if sm.get('src') != ap or sm.get('size') != sz or (sm.get('mtime') is not None and abs(sm['mtime'] - mt) > 1e-3): continue
            if json.load(open(os.path.join(d, 'meta.json'))).get('phase') != 'done': continue
            if best is None or (sm.get('built') or 0) > best[0]: best = (sm.get('built') or 0, d)
        except Exception: continue
    return best[1] if best else None

def ensure(path, force=False, log=print):
    from . import build
    d = model_dir(path)
    if force or not os.path.exists(os.path.join(d, 'meta.json')):
        tmp = d + '.tmp'; shutil.rmtree(tmp, ignore_errors=True)
        build.convert(path, tmp, log); shutil.rmtree(d, ignore_errors=True); os.rename(tmp, d)
    else: log('cache hit: %s' % d)
    return d

def hypr_env():
    env = dict(os.environ)
    if not env.get('HYPRLAND_INSTANCE_SIGNATURE'):
        d = os.path.join(env.get('XDG_RUNTIME_DIR', '/run/user/%d' % os.getuid()), 'hypr')
        try:
            c = sorted((os.path.getmtime(os.path.join(d, x)), x) for x in os.listdir(d) if os.path.exists(os.path.join(d, x, '.socket.sock')))
            if c: env['HYPRLAND_INSTANCE_SIGNATURE'] = c[-1][1]
        except OSError: pass
    return env

def open_browser(url, workspace=None, headless=False):
    prof = os.path.join(reader.CACHE_DIR, 'chromium-profile')
    extra = ['--enable-unsafe-webgpu', '--ignore-gpu-blocklist']
    if os.environ.get('RVT_BALLET_CDP'): extra.append('--remote-debugging-port=' + os.environ['RVT_BALLET_CDP'])
    if workspace and sys.platform.startswith('linux') and shutil.which('hyprctl'):       # Hyprland placement only where it exists
        import shlex
        cmd = plat.browser.app_command(url, prof, extra=extra) or ['chromium', '--app=' + url, '--user-data-dir=' + prof] + extra
        code = 'hl.dispatch(hl.dsp.exec_cmd(%s))' % json.dumps('[workspace %s silent] %s' % (workspace, ' '.join(shlex.quote(c) for c in cmd)))
        subprocess.run(['hyprctl', 'eval', code], env=hypr_env())
    else: plat.browser.open_app(url, prof, extra=extra)

def stale_mark(d):
    try:
        st = json.load(open(os.path.join(d, 'meta.json'))).get('stamps') or {}
        return '' if st.get('reader') == reader.reader_stamp() and st.get('viewer') == reader.viewer_stamp() else ' (stale: reader/viewer changed, reopen the .rvt to reconvert)'
    except Exception: return ''

def dir_size(d):
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)

def prepare(files):
    """--prepare: fully convert + cache each model (Rust fast path, own capped process), ask the sheets session to pre-render all sheets/views (`rvt-sheets warm FILE`, see ~/src/rvt-sheets/HOOKS.md),
    then print READY with the exact demo command and what is cached"""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sheets_cli = os.path.expanduser('~/src/rvt-sheets/rvt-sheets'); summary = []
    for f in files:
        f = os.path.abspath(f)
        if not os.path.isfile(f): print('not a file: ' + f); continue
        d = model_dir(f); t = time.time(); line = {'file': f}
        done = os.path.exists(os.path.join(d, 'meta.json')) and json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done'
        if done: print('[model] %s: already cached (%s)' % (os.path.basename(f), d)); line['model'] = 'cached'
        else:
            print('[model] converting %s (progress: see the banner when opened; this runs the capped converter) ...' % os.path.basename(f), flush=True)
            r = subprocess.run([os.path.join(here, 'rvt-ballet'), 'convert', f, d], env=dict(os.environ, RVT_MAT_PY_MB=os.environ.get('RVT_MAT_PY_MB', '60')))      # offline prep: per-face materials (Python meshes) up to 60 MB
            if r.returncode != 0: print('[model] conversion FAILED (exit %d)' % r.returncode); line['model'] = 'FAILED'; summary.append(line); continue
            line['model'] = 'converted in %.0f s' % (time.time() - t)
        sm = {}
        try: sm = json.load(open(os.path.join(d, 'summary.json')))
        except Exception: pass
        line['dir'] = d; line['size_mb'] = round(dir_size(d) / 1e6, 1); line['elements'] = sm.get('elements')
        # sheets warm (owned by rvt-sheets; do not duplicate its caching)
        t = time.time()
        if os.path.exists(sheets_cli):
            big = os.path.getsize(f) > float(os.environ.get('RVT_WARM_HOST1_MB', '15')) * 1e6 and os.path.exists(os.path.expanduser('~/.local/share/offload/h1run'))
            r = subprocess.run([sheets_cli, 'warm', f] + (['--host1'] if big else []), capture_output=True, text=True); out = (r.stdout or '') + (r.stderr or '')
            if big and r.returncode != 0 and 'warmed' not in out and os.environ.get('RVT_WARM_NO_LOCAL'): print('[sheets] host1 warm failed, local warm disabled (RVT_WARM_NO_LOCAL)')
            elif big and r.returncode != 0 and 'warmed' not in out:       # host1 busy/unreachable: warm here, niced
                print('[sheets] host1 warm failed (%s): warming locally' % out.strip()[-160:]); r = subprocess.run(['nice', '-n', '15', sheets_cli, 'warm', f], capture_output=True, text=True); out = (r.stdout or '') + (r.stderr or '')
            if r.returncode == 0: line['sheets'] = 'warmed in %.0f s' % (time.time() - t); print('[sheets] warm ok:\n' + out.strip()[-600:])
            elif 'invalid choice' in out or 'usage' in out.lower() or 'unknown' in out.lower(): line['sheets'] = 'NOT warmed: rvt-sheets has no `warm` command yet (sheets render on first open)'; print('[sheets] ' + line['sheets'])
            else: line['sheets'] = 'warm failed (exit %d)' % r.returncode; print('[sheets] ' + line['sheets'] + '\n' + out.strip()[-400:])
        else: line['sheets'] = 'rvt-sheets not installed'; print('[sheets] not installed (%s)' % sheets_cli)
        summary.append(line)
    sc = os.path.expanduser('~/.cache/rvt-sheets'); nsc = len(os.listdir(sc)) if os.path.isdir(sc) else 0
    print('\nCached:')
    for l in summary: print('  %s: model %s (%s MB, %s elements) | sheets: %s' % (os.path.basename(l['file']), l.get('model'), l.get('size_mb'), l.get('elements'), l.get('sheets')))
    print('  sheets cache directory ~/.cache/rvt-sheets: %d entries' % nsc)
    for l in summary:
        if l.get('model') != 'FAILED': print('\nREADY: %s %s --sheets' % (os.path.join(here, 'bin', 'rvt-view'), l['file']))

def main(argv=None):
    ap = argparse.ArgumentParser(prog='rvt-ballet'); sub = ap.add_subparsers(dest='cmd', required=True)
    o = sub.add_parser('open'); o.add_argument('files', nargs='+'); o.add_argument('--port', type=int, default=0); o.add_argument('--no-browser', action='store_true'); o.add_argument('--workspace'); o.add_argument('--rebuild', action='store_true'); o.add_argument('--sheets', action='store_true', help='open directly on the sheets page'); o.add_argument('--hide', default='', help='comma list of categories hidden at start, e.g. Planting,Entourage (URL ?hide=...)'); o.add_argument('--prepare', action='store_true', help='demo prep: convert + cache the model(s), warm the sheets cache, print the exact demo command, do not serve')
    c = sub.add_parser('convert'); c.add_argument('file'); c.add_argument('out', nargs='?')
    s = sub.add_parser('serve'); s.add_argument('dirs', nargs='*'); s.add_argument('--port', type=int, default=0)
    a = ap.parse_args(argv)
    from . import server
    if a.cmd in ('open', 'convert'):
        bad = [(f, check_input(f)) for f in (a.files if a.cmd == 'open' else [a.file])]
        bad = [(f, m) for f, m in bad if m]
        if bad:
            for f, m in bad: print('rvt-view: ' + m, file=sys.stderr)
            if a.cmd == 'convert' or len(bad) == len(a.files): sys.exit(2)
            a.files = [f for f in a.files if f not in {b[0] for b in bad}]
    if a.cmd == 'open' and a.prepare: return prepare(a.files)
    if a.cmd == 'convert':
        if not os.environ.get('RVT_CAPPED') and not os.environ.get('RVT_NO_CAP'):
            # every conversion runs under a memory cap + low priority (the reader can balloon on big files); Job Object on Windows, systemd-run on Linux
            env = dict(os.environ, RVT_CAPPED='1')
            gb = float(os.environ.get('RVT_MEM_CAP', '6G').rstrip('GgMm') or 6) / (1024 if os.environ.get('RVT_MEM_CAP', '6G')[-1:] in 'Mm' else 1)
            p = plat.proc.popen_capped([sys.executable, '-c', "import sys; sys.path.insert(0,%r); from rvtballet.cli import main; main(sys.argv[1:])" % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))] + (list(argv) if argv is not None else sys.argv[1:]), mem_gb=gb, env=env)
            sys.exit(p.wait())
        from . import build
        out = a.out or model_dir(a.file)
        try: build.convert(a.file, out)
        except Exception as ex:
            msg = friendly_error(ex); print('rvt-view: cannot convert %s: %s' % (os.path.basename(a.file), msg), file=sys.stderr)
            try: json.dump({'stage': 'error', 'msg': 'Cannot open this file: ' + msg, 'pct': 0, 'stages': []}, open(os.path.join(out, 'progress.json'), 'w'))
            except OSError: pass
            sys.exit(1)
        print(out); return
    models = server.Models()
    import threading

    def start_job(f, rebuild=False):
        """convert f in a separate process (UI polls progress.json); on success the finished directory replaces the building one"""
        d = model_dir(f); tmp = d + '.tmp'; mid = os.path.basename(d)
        shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        models.add(mid, tmp, os.path.basename(f), building=True); models.m[mid]['src'] = f
        def job():
            p = subprocess.Popen([sys.executable, '-c', "import sys; sys.path.insert(0,%r); from rvtballet.cli import main; main(['convert', %r, %r])" % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f, tmp)], stdout=sys.stdout, stderr=sys.stderr)
            if p.wait() == 0 and os.path.exists(os.path.join(tmp, 'meta.json')):
                shutil.rmtree(d, ignore_errors=True); os.rename(tmp, d); models.m[mid]['dir'] = d; models.m[mid]['building'] = False; models.m[mid]['db'] = None
            else:
                try:
                    pj = os.path.join(tmp, 'progress.json'); cur = json.load(open(pj)) if os.path.exists(pj) else {}
                    if cur.get('stage') != 'error': open(pj, 'w').write(json.dumps({'stage': 'error', 'msg': 'conversion failed - see the terminal output', 'pct': 0, 'stages': []}))
                except OSError: pass
        threading.Thread(target=job, daemon=True).start(); return mid
    def open_path(f, fresh=False):
        d = model_dir(f); mid = os.path.basename(d)
        if os.path.exists(os.path.join(d, 'meta.json')) and json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done':
            models.add(mid, d, os.path.basename(f)); models.m[mid]['src'] = f; return mid
        old = None if fresh or os.environ.get('RVT_FRESH') else best_cached(f)
        if old:                                                          # an older complete conversion: open it now, the page offers the update (never a cold conversion in a demo)
            print('cache hit (older reader/converter version, update offered in the page): %s' % old); mid = os.path.basename(old)
            models.add(mid, old, os.path.basename(f)); models.m[mid]['src'] = f; return mid
        return start_job(f)
    models.open_path = open_path
    models.reconvert = lambda mid: start_job(models.m[mid]['src']) if models.m.get(mid, {}).get('src') else None
    if a.cmd == 'open':
        for f in a.files:
            if a.rebuild: start_job(f)
            else: open_path(f)
    else:
        for d in a.dirs: models.add(os.path.basename(d.rstrip('/')), d, os.path.basename(d.rstrip('/')))
        root = os.path.join(reader.CACHE_DIR, 'models')
        if not a.dirs and os.path.isdir(root):
            for n in sorted(os.listdir(root)):
                if os.path.exists(os.path.join(root, n, 'meta.json')): models.add(n, os.path.join(root, n), n.rsplit('-', 1)[0] + stale_mark(os.path.join(root, n)))
    def ready(port):
        first = next(iter(models.m)) if models.m else ''
        qs = '&'.join(x for x in ['sheets=1' if getattr(a, 'sheets', False) else '', 'hide=' + urllib.parse.quote(a.hide) if getattr(a, 'hide', '') else ''] if x)
        url = 'http://127.0.0.1:%d/%s#%s' % (port, '?' + qs if qs else '', first)
        print('serving', url, flush=True)
        if a.cmd == 'open' and not a.no_browser: open_browser(url, a.workspace)
    server.serve(models, port=a.port, ready=ready)

if __name__ == '__main__': main()
