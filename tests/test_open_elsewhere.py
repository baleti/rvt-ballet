"""open_elsewhere finds another process that holds the file open (Linux /proc), ignores our own handle, returns [] for a closed file and for a missing path."""
import os, sys, subprocess, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.openelsewhere import open_elsewhere
if not os.path.isdir('/proc/self/fd'): print('skipped (no /proc)'); sys.exit(0)
d = tempfile.mkdtemp(); f = os.path.join(d, 'a.rvt'); open(f, 'wb').write(b'x')
mine = open(f, 'rb')                              # our own handle must not count
assert open_elsewhere(f) == [], open_elsewhere(f)
p = subprocess.Popen([sys.executable, '-c', 'import sys,time; h=open(sys.argv[1],"rb"); print("up",flush=True); time.sleep(30)', f], stdout=subprocess.PIPE, text=True)
try:
    p.stdout.readline(); r = open_elsewhere(f); assert r and any('python' in x for x in r), r
finally: p.kill(); p.wait()
time.sleep(0.2); assert open_elsewhere(f) == [], open_elsewhere(f)
assert open_elsewhere(os.path.join(d, 'nope.rvt')) == []
mine.close(); print('OK')
