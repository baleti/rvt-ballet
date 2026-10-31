"""regressions from the second code review (stand-ins, no scene needed): worker death classification (SIGSEGV is NOT 'too_big', SIGABRT/SIGKILL/allocator messages are), truncated worker result, a delete cannot share a save with
edits in other partitions, temp directories are removed when a later pass fails, a deleted element is not also listed as modified, limited verify turns an empty-members stream into LightVerifyFailed."""
import os, sys, types, tempfile, subprocess, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
from rvtballet import save, edit, lightverify
if not save.SaveSessions().available: print('skip'); raise SystemExit
# --- worker classification
ad = save._cached_adapter()(elements_fn=None); real = subprocess.run
def fake(rc, stderr='', write=None):
    def run(cmd, **kw):
        if write is not None: open(cmd[4], 'wb').write(write)
        return subprocess.CompletedProcess(cmd, rc, '', stderr)
    return run
try:
    for rc, err, cls in ((-11, '', RuntimeError), (-6, '', save.TooBig), (-9, '', save.TooBig), (1, 'memory allocation of 99 bytes failed', save.TooBig), (1, 'Traceback...', RuntimeError)):
        subprocess.run = fake(rc, err)
        try: ad._snapshot_in_worker(b'x'); raise SystemExit('FAIL: no error for rc %s' % rc)
        except cls as e: assert type(e) is cls, (rc, type(e))
    subprocess.run = fake(0, '', write=b'\x80\x04truncated')                  # killed mid-write: unreadable result -> RuntimeError (422 output_unreadable), not an unmapped 500
    try: ad._snapshot_in_worker(b'x'); raise SystemExit('FAIL: truncated result accepted')
    except RuntimeError as e: assert 'unreadable result' in str(e)
finally: subprocess.run = real
# --- multi-partition: delete + edits in other partitions refused; intermediate files removed after a failing pass
class FakeCFB:
    def __init__(self, b): pass
    def streams(self): return {'Partitions/1': 1, 'Partitions/2': 2, 'Global/Latest': 3}
fake_cfb = types.ModuleType('cfb'); fake_cfb.CFB = FakeCFB; real_cfb = sys.modules.get('cfb'); sys.modules['cfb'] = fake_cfb
calls = []
class FakeEdit:
    def __init__(self, path):
        self.path = path; self.g = types.SimpleNamespace(e=types.SimpleNamespace(m=types.SimpleNamespace(parts={'a': 1, 'b': 2}), trace=lambda eid: ('Partitions/%d' % (1 if eid < 100 else 2), 0, {'class': 'FamilyInstance'}, [])))
    def move(self, eid, dx, dy, dz): calls.append(('move', eid, os.environ.get('PART')))
    def set_string(self, eid, old, new):
        if eid == 777: raise RuntimeError('boom in the second pass')
    def save(self, dst): open(dst, 'wb').write(b'x')
fake_edit = types.ModuleType('rvtedit'); fake_edit.Edit = FakeEdit; real_edit = sys.modules.get('rvtedit'); sys.modules['rvtedit'] = fake_edit
dirs = []; real_mk = tempfile.mkdtemp
def mk(*a, **k): d = real_mk(*a, **k); dirs.append(d); return d
tempfile.mkdtemp = mk
try:
    dele = edit.validate_op({'op': 'delete', 'eid': 5}); mv = edit.validate_op({'op': 'move', 'eid': 500, 'dx': 1.0})
    try: edit.apply(b'src', [dele, mv]); raise SystemExit('FAIL: delete + other partition accepted')
    except edit.EditError as e: assert 'delete cannot be saved together' in str(e), e
    ok = edit.validate_op({'op': 'move', 'eid': 5, 'dx': 1.0}); bad = edit.validate_op({'op': 'set_string', 'eid': 777, 'value': 'x'})      # 777 lives in partition 2: runs as the 2nd pass and fails
    dirs.clear()
    try: edit.apply(b'src', [ok, bad]); raise SystemExit('FAIL: failing pass accepted')
    except edit.EditError as e: assert 'boom' in str(e), e
    assert dirs and not any(os.path.exists(d) for d in dirs), 'temp dir (with the pass-0 copy) leaked: %s' % [d for d in dirs if os.path.exists(d)]
finally:
    tempfile.mkdtemp = real_mk
    if real_cfb is None: sys.modules.pop('cfb', None)
    else: sys.modules['cfb'] = real_cfb
    if real_edit is None: sys.modules.pop('rvtedit', None)
    else: sys.modules['rvtedit'] = real_edit
# --- manifest: a deleted element is not also 'modified'
e = edit.Edits(); e.ops = [edit.validate_op({'op': 'move', 'eid': 5, 'dx': 1.0}), edit.validate_op({'op': 'delete', 'eid': 6})]
m = e.manifest([5, 6]); assert m == {'modified': [], 'deleted': ['el:5', 'el:6'], 'must_delete': ['el:6']}, m
# --- limited verify: no gzip members at all -> LightVerifyFailed (not ValueError)
WL = edit.WL
if os.path.exists(os.path.join(WL, 'cfb.py')):
    sys.path.insert(0, WL); import cfb, rvtw
    scene = os.path.join(WL, 'scenes/classtests/2024_writer_cols2.rte')
    if os.path.exists(scene):
        buf = open(scene, 'rb').read(); c = cfb.CFB(buf); st = c.streams()['Partitions/61']; s = rvtw.Stream(st.data); st.data = s.build(b'\0' * len(s.payload), keep_spare=True); p = os.path.join(tempfile.mkdtemp(), 'nomembers.rvt'); cfb.write(c, p)
        try: lightverify.light_verify(buf, open(p, 'rb').read(), 1); raise SystemExit('FAIL: stream without gzip members accepted')
        except lightverify.LightVerifyFailed: pass
print('save review2 OK: worker classification, truncated result, delete across partitions refused, temp cleanup, manifest, no-members')
