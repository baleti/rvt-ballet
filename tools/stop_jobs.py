"""stop background jobs started by the viewer tools (matches command lines, never itself): tools/stop_jobs.py [accept|regress|conv ...]"""
import os, sys, signal
pats = sys.argv[1:] or ['accept_eval.py', 'accept_all.sh']; me = os.getpid(); n = 0
for d in os.listdir('/proc'):
    if not d.isdigit() or int(d) == me: continue
    try: cmd = open('/proc/%s/cmdline' % d, 'rb').read().decode(errors='ignore')
    except OSError: continue
    if 'stop_jobs.py' in cmd: continue
    if any(p in cmd for p in pats):
        try: os.kill(int(d), signal.SIGTERM); n += 1
        except OSError: pass
print('stopped', n)
