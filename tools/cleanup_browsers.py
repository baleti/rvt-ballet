"""kill stale headless Chromium processes started by the test tools (user-data-dir /tmp/rvtv-cdp-*) and remove their profile dirs; safe to run any time.
usage: tools/cleanup_browsers.py [--older-than SECONDS]   (default: everything)"""
import os, sys, signal, shutil, glob, time

def stale(older=0):
    me = os.getpid(); out = []
    for d in os.listdir('/proc'):
        if not d.isdigit() or int(d) == me: continue
        try:
            cmd = open('/proc/%s/cmdline' % d, 'rb').read().replace(b'\0', b' ').decode(errors='ignore')
            if '--user-data-dir=/tmp/rvtv-cdp-' not in cmd: continue
            age = time.time() - os.stat('/proc/%s' % d).st_mtime
            if age >= older: out.append(int(d))
        except OSError: continue
    return out

def main():
    older = int(sys.argv[sys.argv.index('--older-than') + 1]) if '--older-than' in sys.argv else 0
    pids = stale(older)
    for p in pids:
        try: os.kill(p, signal.SIGTERM)
        except OSError: pass
    time.sleep(1.5)
    for p in stale(older):
        try: os.kill(p, signal.SIGKILL)
        except OSError: pass
    live = {os.path.basename(x) for x in glob.glob('/tmp/rvtv-cdp-*')}
    for d in glob.glob('/tmp/rvtv-cdp-*') + glob.glob('/tmp/rvtv-timing-*'):
        shutil.rmtree(d, ignore_errors=True)
    print('killed', len(pids), 'browser processes; remaining', len(stale(0)))

if __name__ == '__main__': main()
