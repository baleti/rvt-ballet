"""rvt-viewer open FILE.rvt | convert FILE.rvt OUTDIR | serve [DIRS...]"""
import os, sys, argparse, hashlib, json, subprocess, shutil, time
from . import reader

def model_dir(path):
    key = hashlib.md5(('%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader.reader_stamp() + BUILD_VERSION)).encode()).hexdigest()[:12]
    return os.path.join(reader.CACHE_DIR, 'models', os.path.splitext(os.path.basename(path))[0] + '-' + key)

BUILD_VERSION = 'b1'

def ensure(path, force=False, log=print):
    from . import build
    d = model_dir(path)
    if force or not os.path.exists(os.path.join(d, 'meta.json')):
        tmp = d + '.tmp'; shutil.rmtree(tmp, ignore_errors=True)
        build.convert(path, tmp, log); shutil.rmtree(d, ignore_errors=True); os.rename(tmp, d)
    else: log('cache hit: %s' % d)
    return d

def open_browser(url, workspace=None, headless=False):
    prof = os.path.join(reader.CACHE_DIR, 'chromium-profile')
    cmd = ['chromium', '--app=' + url, '--user-data-dir=' + prof, '--enable-unsafe-webgpu', '--ignore-gpu-blocklist', '--no-first-run', '--window-size=1500,950']
    if workspace:
        sig = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
        subprocess.Popen(['hyprctl', 'dispatch', 'exec', '[workspace %s silent] %s' % (workspace, ' '.join(cmd))])
    else: subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main(argv=None):
    ap = argparse.ArgumentParser(prog='rvt-viewer'); sub = ap.add_subparsers(dest='cmd', required=True)
    o = sub.add_parser('open'); o.add_argument('files', nargs='+'); o.add_argument('--port', type=int, default=0); o.add_argument('--no-browser', action='store_true'); o.add_argument('--workspace'); o.add_argument('--rebuild', action='store_true')
    c = sub.add_parser('convert'); c.add_argument('file'); c.add_argument('out', nargs='?')
    s = sub.add_parser('serve'); s.add_argument('dirs', nargs='*'); s.add_argument('--port', type=int, default=0)
    a = ap.parse_args(argv)
    from . import server
    if a.cmd == 'convert':
        from . import build
        out = a.out or model_dir(a.file); build.convert(a.file, out); print(out); return
    models = server.Models()
    if a.cmd == 'open':
        for f in a.files:
            d = ensure(f, a.rebuild); models.add(os.path.basename(d), d, os.path.basename(f))
    else:
        for d in a.dirs: models.add(os.path.basename(d.rstrip('/')), d, os.path.basename(d.rstrip('/')))
        root = os.path.join(reader.CACHE_DIR, 'models')
        if not a.dirs and os.path.isdir(root):
            for n in sorted(os.listdir(root)):
                if os.path.exists(os.path.join(root, n, 'meta.json')): models.add(n, os.path.join(root, n), n)
    def ready(port):
        first = next(iter(models.m)) if models.m else ''
        url = 'http://127.0.0.1:%d/#%s' % (port, first)
        print('serving', url, flush=True)
        if a.cmd == 'open' and not a.no_browser: open_browser(url, a.workspace)
    server.serve(models, port=a.port, ready=ready)

if __name__ == '__main__': main()
