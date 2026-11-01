"""RLIMIT_FSIZE sweep (full-disk analogue) for in-place SAVE! on RVT scenes (synthetic writer scenes, public-safe): limits at 0,10,50,90,99,100 % of the file size.
Invariants: refused with a disk error OR (limit >= new size) saved; original byte-identical after every refusal; no .tmp/.part/.sgtmp; every listed backup has the ORIGINAL bytes. usage: tools/rvt_efbig_sweep.py [FILE EID]"""
import os, sys, shutil, hashlib, tempfile, signal, resource
base = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = base + '/j'; os.environ['SAVEGATE_CACHE'] = base + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = base + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(base + '/gate.json', 'w').write('{"rvt": {"2024": "open", "2026": "open"}}'); os.environ['SAVEGATE_GATE'] = base + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CASES = [(os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'), 301595)] if len(sys.argv) < 3 else [(sys.argv[1], int(sys.argv[2]))]
bad = 0
for S, eid in CASES:
    for pct in (0, 10, 50, 90, 99, 100):
        p = base + '/m.rte'; shutil.copy(S, p); h0 = sha(p); size = os.path.getsize(p)
        for b in list(save.backups(p)): pass
        ss = save.SaveSessions(); d = ss.doc('m', p)
        nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': eid, 'dx': 1.0})])
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN); resource.setrlimit(resource.RLIMIT_FSIZE, (size * pct // 100, resource.RLIM_INFINITY))
        try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % eid]}); res = 'saved'
        except Exception as e: res = 'refused:' + type(e).__name__
        resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        left = [f for f in os.listdir(base) if f.endswith(('.tmp', '.part', '.sgtmp'))]
        bk = [b for b in save.backups(p) if sha(b['path']) != h0]
        ok = (res.startswith('refused') and sha(p) == h0) or (res == 'saved' and open(p, 'rb').read() == nb)
        if not ok or left or bk or 'GateClosed' in res: bad += 1
        print('%s pct=%3d -> %s original_intact=%s new_ok=%s temp_left=%d bad_backups=%d' % (os.path.basename(S)[:18], pct, res, sha(p) == h0, open(p, 'rb').read() == nb, len(left), len(bk)))
        for f in left: os.remove(os.path.join(base, f))
        os.remove(p)
print('EFBIG SWEEP', 'FAIL %d' % bad if bad else 'OK')
sys.exit(1 if bad else 0)
