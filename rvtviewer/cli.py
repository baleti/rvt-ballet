"""rvt-viewer open FILE.rvt | convert FILE.rvt OUTDIR | serve [DIRS...]"""
import os, sys, argparse, hashlib, json, subprocess, shutil, time
from . import reader

def model_dir(path):
    key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader.reader_stamp() + reader.viewer_stamp())).encode()).hexdigest()[:12]
    return os.path.join(reader.CACHE_DIR, 'models', os.path.splitext(os.path.basename(path))[0] + '-' + key)

BUILD_VERSION = 'b3'

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
    cmd = ['chromium', '--app=' + url, '--user-data-dir=' + prof, '--enable-unsafe-webgpu', '--ignore-gpu-blocklist', '--no-first-run', '--window-size=1500,950']
    if os.environ.get('RVT_VIEWER_CDP'): cmd.append('--remote-debugging-port=' + os.environ['RVT_VIEWER_CDP'])
    if workspace:
        import shlex
        code = 'hl.dispatch(hl.dsp.exec_cmd(%s))' % json.dumps('[workspace %s silent] %s' % (workspace, ' '.join(shlex.quote(c) for c in cmd)))
        subprocess.run(['hyprctl', 'eval', code], env=hypr_env())
    else: subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def stale_mark(d):
    try:
        st = json.load(open(os.path.join(d, 'meta.json'))).get('stamps') or {}
        return '' if st.get('reader') == reader.reader_stamp() and st.get('viewer') == reader.viewer_stamp() else ' (stale: reader/viewer changed, reopen the .rvt to reconvert)'
    except Exception: return ''

def main(argv=None):
    ap = argparse.ArgumentParser(prog='rvt-viewer'); sub = ap.add_subparsers(dest='cmd', required=True)
    o = sub.add_parser('open'); o.add_argument('files', nargs='+'); o.add_argument('--port', type=int, default=0); o.add_argument('--no-browser', action='store_true'); o.add_argument('--workspace'); o.add_argument('--rebuild', action='store_true'); o.add_argument('--sheets', action='store_true', help='open directly on the sheets page')
    c = sub.add_parser('convert'); c.add_argument('file'); c.add_argument('out', nargs='?')
    s = sub.add_parser('serve'); s.add_argument('dirs', nargs='*'); s.add_argument('--port', type=int, default=0)
    a = ap.parse_args(argv)
    from . import server
    if a.cmd == 'convert':
        if not os.environ.get('RVT_CAPPED') and not os.environ.get('RVT_NO_CAP') and shutil.which('systemd-run'):
            # every conversion runs under a memory cap + nice (the reader can balloon on big files)
            env = dict(os.environ, RVT_CAPPED='1')
            os.execvpe('systemd-run', ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=' + os.environ.get('RVT_MEM_CAP', '6G'), '-p', 'MemorySwapMax=0', 'nice', '-n', '10', sys.executable, '-c',
                       "import sys; sys.path.insert(0,%r); from rvtviewer.cli import main; main(sys.argv[1:])" % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))] + (list(argv) if argv is not None else sys.argv[1:]), env)
        from . import build
        out = a.out or model_dir(a.file); build.convert(a.file, out); print(out); return
    models = server.Models()
    import threading

    def start_job(f, rebuild=False):
        """convert f in a separate process (UI polls progress.json); on success the finished directory replaces the building one"""
        d = model_dir(f); tmp = d + '.tmp'; mid = os.path.basename(d)
        shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        models.add(mid, tmp, os.path.basename(f), building=True); models.m[mid]['src'] = f
        def job():
            p = subprocess.Popen([sys.executable, '-c', "import sys; sys.path.insert(0,%r); from rvtviewer.cli import main; main(['convert', %r, %r])" % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f, tmp)], stdout=sys.stdout, stderr=sys.stderr)
            if p.wait() == 0 and os.path.exists(os.path.join(tmp, 'meta.json')):
                shutil.rmtree(d, ignore_errors=True); os.rename(tmp, d); models.m[mid]['dir'] = d; models.m[mid]['building'] = False; models.m[mid]['db'] = None
            else:
                try: open(os.path.join(tmp, 'progress.json'), 'w').write(json.dumps({'stage': 'error', 'msg': 'conversion failed - see the terminal output', 'pct': 0, 'stages': []}))
                except OSError: pass
        threading.Thread(target=job, daemon=True).start(); return mid
    def open_path(f):
        d = model_dir(f); mid = os.path.basename(d)
        if os.path.exists(os.path.join(d, 'meta.json')) and json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done':
            models.add(mid, d, os.path.basename(f)); models.m[mid]['src'] = f; return mid
        return start_job(f)
    models.open_path = open_path
    models.reconvert = lambda mid: start_job(models.m[mid]['src']) if models.m.get(mid, {}).get('src') else None
    if a.cmd == 'open':
        for f in a.files:
            d = model_dir(f)
            if os.path.exists(os.path.join(d, 'meta.json')) and not a.rebuild and json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done':
                print('cache hit: %s' % d); models.add(os.path.basename(d), d, os.path.basename(f)); models.m[os.path.basename(d)]['src'] = f
            else: start_job(f)
    else:
        for d in a.dirs: models.add(os.path.basename(d.rstrip('/')), d, os.path.basename(d.rstrip('/')))
        root = os.path.join(reader.CACHE_DIR, 'models')
        if not a.dirs and os.path.isdir(root):
            for n in sorted(os.listdir(root)):
                if os.path.exists(os.path.join(root, n, 'meta.json')): models.add(n, os.path.join(root, n), n.rsplit('-', 1)[0] + stale_mark(os.path.join(root, n)))
    def ready(port):
        first = next(iter(models.m)) if models.m else ''
        url = 'http://127.0.0.1:%d/%s#%s' % (port, '?sheets=1' if getattr(a, 'sheets', False) else '', first)
        print('serving', url, flush=True)
        if a.cmd == 'open' and not a.no_browser: open_browser(url, a.workspace)
    server.serve(models, port=a.port, ready=ready)

if __name__ == '__main__': main()
