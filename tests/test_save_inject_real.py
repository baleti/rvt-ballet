"""Interrupt/OSError injected at every step of an in-place overwrite of a REAL 2024 .rte (RVT adapter, edit applied): afterwards the file is exactly the old or exactly the new bytes
(new one clean by the gate), no .sgtmp / lock left, and the next save succeeds. Real-file counterpart of savegate tests/test_crash_injection.py."""
import os, sys, hashlib, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/src/savegate'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg
from savegate import core, atomic
from savegate.adapters import RvtAdapter
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
STEPS = [(core, '_produce'), (core, 'check_unchanged'), (core, 'make_backup'), (atomic, 'commit_temp'), (core, '_finish_check'), (atomic, 'full_fsync'), (atomic, 'fsync_dir')]
bad = []; n = 0
try:
    for mod, name in STEPS:
        for exc in (KeyboardInterrupt, MemoryError, OSError):
            d = T + '/d%d' % n; os.makedirs(d); src = d + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src); n += 1
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
            nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
            real = getattr(mod, name); c = {'n': 0}
            def boom(*a, _r=real, _c=c, _e=exc, _nm=name, **k):
                _c['n'] += 1
                if _c['n'] == 1 or (_nm == 'check_unchanged' and _c['n'] == 2): raise _e()
                return _r(*a, **k)
            setattr(mod, name, boom)
            try: save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); raised = False
            except BaseException as e: raised = True
            finally: setattr(mod, name, real)
            h = sha(src); st = 'old' if h == h0 else 'new'
            dmg = bool(RvtAdapter().source_damage(open(src, 'rb').read()))
            left = [x for x in os.listdir(d) if x.endswith('.sgtmp') or x.endswith('savegate-lock')]
            ok = not dmg and not left
            try:      # next save must work
                ss2 = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd2 = ss2.doc('m', src)
                nb2, _ = edit.apply_full(dd2.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
                save.save_overwrite(ss2, 'm', src, new_bytes=nb2, manifest={'modified': ['el:301595']})
            except BaseException as e: ok = False; st += ' nextsave:%s' % type(e).__name__
            if not ok: bad.append((name, exc.__name__, st, dmg, left))
            print(name, exc.__name__, 'raised' if raised else 'noraise', st, 'dmg', dmg, 'left', left, flush=True)
    assert not bad, bad
    print('OK', n, 'cases')
finally: shutil.rmtree(T, ignore_errors=True)
