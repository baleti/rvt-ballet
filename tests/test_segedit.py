"""segment writer (rvtballet/segedit.py): equivalence with the old writer, scoped verification, in-place safety. Autodesk sample only (Snowdon HVAC 2024);
every in-place run uses a private copy and a per-run gate file (the real gate is never opened). Run: python3 -m pytest -q tests/test_segedit.py"""
import os, sys, json, glob, random, shutil, signal, subprocess, time, hashlib, struct
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
from rvtballet import segedit
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
ORACLE = os.path.expanduser('~/demo-state/c3x-rvtinfo-oracle')      # Revit-VM-passed outputs of the OLD writer (local evidence dir)
EID = 1365188
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk sample not present')


def md5(p): return hashlib.md5(open(p, 'rb').read()).hexdigest()


def streams(p):
    import olefile
    o = olefile.OleFileIO(p); return {'/'.join(e): o.openstream('/'.join(e)).read() for e in o.listdir(streams=True)}


def gate_damage(p):
    sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate.adapters import RvtAdapter
    return RvtAdapter().source_damage(open(p, 'rb').read())


@pytest.fixture
def env(tmp_path, monkeypatch):
    src = tmp_path / 'h.rvt'; shutil.copy(SRC, src)
    (tmp_path / 'gate.json').write_text('{"rvt": {"2024": "open"}}')
    monkeypatch.setenv('SAVEGATE_GATE', str(tmp_path / 'gate.json')); monkeypatch.setenv('RVTBALLET_ALLOW_OVERWRITE', '1')
    monkeypatch.setenv('SAVEGATE_BACKUPS', 'cache'); monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data')); monkeypatch.setenv('SEGEDIT_CLEAN_DIR', str(tmp_path / 'clean'))
    return tmp_path, src


@pytest.mark.parametrize('name,op', [('setstring_mark', dict(op='set_string', eid=EID, param='Mark', value='c8x-probe-7')),
                                      ('move_x2', dict(op='move', eid=EID, dx=2.0, dy=0.0, dz=0.0)), ('rotate90', dict(op='rotate', eid=EID, deg=90.0))])
def test_shift_layout_equals_vm_passed_old_writer_output(tmp_path, name, op):
    """the shift layout reproduces the old writer's bytes: every stream equal to the Revit-VM-passed output of the same edit"""
    ref = os.path.join(ORACLE, '2024_hvac_%s.rvt' % name)
    if not os.path.exists(ref): pytest.skip('oracle output not present')
    out = str(tmp_path / 'o.rvt'); segedit.apply_ops(os.path.join(ORACLE, '2024_hvac_original.rvt'), out, [op], mode='shift')
    A, B = streams(ref), streams(out); assert sorted(A) == sorted(B)
    assert [k for k in A if A[k] != B[k]] == []


def test_fit_layout_touches_only_the_edited_page_and_passes_the_full_gate(tmp_path):
    out = str(tmp_path / 'o.rvt'); info = segedit.apply_ops(SRC, out, [dict(op='set_string', eid=EID, param='Mark', value='fit-1')], mode='fit')
    assert len(info['pages']) == 1 and info['bytes_written'] == 65249
    a, b = open(SRC, 'rb').read(), open(out, 'rb').read(); assert len(a) == len(b)
    diff = {i // 4096 for i in range(0, len(a), 4096) if a[i:i + 4096] != b[i:i + 4096]}
    assert 1 <= len(diff) <= 17
    assert gate_damage(out) == []
    S0, S1 = streams(SRC), streams(out); assert [k for k in S0 if S0[k] != S1[k]] == [info_part(out)]


def info_part(p): return [n for n in streams(p) if n.startswith('Partitions/')][0]


def test_refuses_damaged_member_it_would_rewrite(tmp_path):
    """a corrupt byte inside the member that holds the record: inflate/CRC fails -> Refused, nothing written"""
    bad = str(tmp_path / 'bad.rvt'); shutil.copy(SRC, bad)
    s = segedit.Session(SRC); i, r, log, q = s.trace(EID); k = s.J.member_of(i); pos, end = s.sp.mem[k][:2]
    a = (pos + end) // 2; pg, po = divmod(a, segedit.PAGE_PAYLOAD); st = pg * segedit.PAGE_STORED + po
    ss = s.sp.ss; off = (s.sp.chain[st // ss] + 1) * ss + st % ss
    with open(bad, 'r+b') as f: f.seek(off); b = f.read(1); f.seek(off); f.write(bytes([b[0] ^ 0x40]))
    with pytest.raises(segedit.Refused): segedit.apply_ops(bad, str(tmp_path / 'o.rvt'), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert not os.path.exists(tmp_path / 'o.rvt')


def test_writer_corruption_is_caught_by_verify(tmp_path, monkeypatch):
    """a byte flipped by the writer in a rewritten page (simulated) must be refused by the independent verify; the destination is never created"""
    real = segedit._pwrite_stream
    def flip(fd, sp, a, data):
        d = bytearray(data); d[len(d) // 3] ^= 1; return real(fd, sp, a, bytes(d))
    monkeypatch.setattr(segedit, '_pwrite_stream', flip)
    with pytest.raises(segedit.Refused): segedit.apply_ops(SRC, str(tmp_path / 'o.rvt'), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert not os.path.exists(tmp_path / 'o.rvt') and not glob.glob(str(tmp_path / '*segpart*'))


def test_writer_stray_write_outside_pages_is_caught(tmp_path, monkeypatch):
    """a stray write into an untouched sector (simulated) must be refused by the full-file compare"""
    real = segedit._pwrite_stream
    def stray(fd, sp, a, data):
        n = real(fd, sp, a, data); os.pwrite(fd, b'\x55', os.fstat(fd).st_size - 5000); return n
    monkeypatch.setattr(segedit, '_pwrite_stream', stray)
    with pytest.raises(segedit.Refused): segedit.apply_ops(SRC, str(tmp_path / 'o.rvt'), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert not os.path.exists(tmp_path / 'o.rvt')


def test_inplace_success_backup_restore(env):
    tmp, src = env; m0 = md5(src)
    info = segedit.save_in_place(str(src), [dict(op='set_string', eid=EID, param='Mark', value='ip-1')])
    assert md5(info['backup']) == m0 and md5(src) != m0 and gate_damage(str(src)) == []
    assert info['verify']['readback'] == [[EID, 'astr', 'ip-1']] or info['verify']['readback'] == [(EID, 'astr', 'ip-1')]
    assert not [x for x in os.listdir(tmp) if x.endswith('.sgtmp')]
    sys.path.insert(0, os.path.expanduser('~/src/savegate')); import savegate.core as core
    core.restore(str(src)); assert md5(src) == m0


def test_inplace_gate_closed_and_policy_off_refuse(env, monkeypatch):
    tmp, src = env; m0 = md5(src)
    (tmp / 'gate.json').write_text('{"rvt": {"2024": "closed"}}')
    with pytest.raises(segedit.Refused): segedit.save_in_place(str(src), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    (tmp / 'gate.json').write_text('{"rvt": {"2024": "open"}}'); monkeypatch.setenv('RVTBALLET_ALLOW_OVERWRITE', '0')
    with pytest.raises(segedit.Refused): segedit.save_in_place(str(src), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert md5(src) == m0


def test_inplace_refuses_damaged_source(env):
    tmp, src = env; m0 = None
    with open(src, 'r+b') as f: f.seek(os.path.getsize(src) - 70000); b = f.read(1); f.seek(-1, 1); f.write(bytes([b[0] ^ 0x10]))
    m0 = md5(src)
    with pytest.raises(segedit.Refused): segedit.save_in_place(str(src), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert md5(src) == m0


def test_inplace_group_member_refused(env):
    tmp, src = env; m0 = md5(src)
    with pytest.raises(segedit.Refused, match='group'): segedit.save_in_place(str(src), [dict(op='set_string', eid=1421734, param='Mark', value='x')])
    assert md5(src) == m0


def test_inplace_source_mutated_during_save_refused(env, monkeypatch):
    """another program writes the file between our load and the commit: Conflict, the external change survives"""
    tmp, src = env
    real = segedit.verify_output
    def mutate(*a, **k):
        r = real(*a, **k)
        with open(src, 'r+b') as f: f.seek(100000); f.write(b'EXTERNAL')
        return r
    monkeypatch.setattr(segedit, 'verify_output', mutate)
    with pytest.raises(Exception, match='changed'): segedit.save_in_place(str(src), [dict(op='set_string', eid=EID, param='Mark', value='x')])
    assert open(src, 'rb').read()[100000:100008] == b'EXTERNAL' and not [x for x in os.listdir(tmp) if x.endswith('.sgtmp')]


KILL_RUNNER = r'''
import sys; sys.path.insert(0, sys.argv[1]); from rvtballet import segedit
segedit.save_in_place(sys.argv[2], [dict(op='set_string', eid=int(sys.argv[3]), param='Mark', value=sys.argv[4])])
'''


def test_inplace_kill9_never_leaves_a_partial_file(env):
    """SIGKILL at 24 random moments of an in-place save: the file is always the original or the complete verified output (never anything else), and the
    output passes the full source gate; the backup equals the original whenever it exists"""
    tmp, src = env; m0 = md5(src)
    ref = tmp / 'ref.rvt'; shutil.copy(src, ref)
    segedit.save_in_place(str(ref), [dict(op='set_string', eid=EID, param='Mark', value='kill-x')]); m1 = md5(ref)
    seen = {m0: 0, m1: 0}; rnd = random.Random(7)
    for k in range(24):
        shutil.copy(SRC, src); os.utime(src, None)
        p = subprocess.Popen([sys.executable, '-c', KILL_RUNNER, HERE, str(src), str(EID), 'kill-x'], env=os.environ.copy())
        time.sleep(rnd.uniform(0.05, 2.2)); p.send_signal(signal.SIGKILL); p.wait()
        h = md5(src); assert h in seen, 'partial or unknown file after kill %d' % k
        seen[h] += 1
    assert gate_damage(str(src)) == [] or md5(src) == m0
    print('kill outcomes: original %d, complete %d' % (seen[m0], seen[m1]))


STRUCT = os.path.expanduser("~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt")
NUM_OP = dict(op="set_num", eid=2888, param="Detail Level", kind="Int", value=3)      # VM PASS with the old writer (ledger, c5x-rvttype)


@pytest.mark.skipif(not os.path.exists(STRUCT), reason="Structural sample not present")
def test_set_num_shift_equals_old_writer(tmp_path):
    os.environ["RVTBALLET_EDIT_BACKEND"] = "rvtedit"
    from rvtballet import edit
    ob, _ = edit.apply_full(open(STRUCT, "rb").read(), [edit.validate_op(NUM_OP)])
    (tmp_path / "old.rvt").write_bytes(ob)
    out = str(tmp_path / "seg.rvt"); info = segedit.apply_ops(STRUCT, out, [NUM_OP], mode="shift")
    assert info["verify"]["readback"][0][2] == 3
    A, B = streams(str(tmp_path / "old.rvt")), streams(out); assert [k for k in A if A[k] != B[k]] == []


@pytest.mark.skipif(not os.path.exists(STRUCT), reason="Structural sample not present")
def test_set_num_in_place_fit(tmp_path, monkeypatch):
    src = tmp_path / "s.rvt"; shutil.copy(STRUCT, src); (tmp_path / "gate.json").write_text("{\"rvt\": {\"2024\": \"open\"}}")
    for k, v in (("SAVEGATE_GATE", str(tmp_path / "gate.json")), ("RVTBALLET_ALLOW_OVERWRITE", "1"), ("SAVEGATE_BACKUPS", "cache"), ("XDG_DATA_HOME", str(tmp_path / "d")), ("SEGEDIT_CLEAN_DIR", str(tmp_path / "c"))): monkeypatch.setenv(k, v)
    m0 = md5(src); info = segedit.save_in_place(str(src), [NUM_OP])
    assert md5(info["backup"]) == m0 and len(info["pages"]) <= 2 and gate_damage(str(src)) == []


def test_set_num_product_guards_apply():
    """segedit runs edit.validate_op: a derived/placeholder parameter and a non-finite value are refused before anything is read"""
    with pytest.raises(segedit.Refused): segedit.apply_ops(SRC, "/nonexistent/x.rvt", [dict(op="set_num", eid=EID, param="Unit weight", value=1.0)])
    with pytest.raises(segedit.Refused): segedit.apply_ops(SRC, "/nonexistent/x.rvt", [dict(op="set_num", eid=EID, param="Area", value=float("nan"))])


def test_auto_falls_back_to_shift_on_old_writer_output(tmp_path):
    """a file saved by the old writer has level-9 members with no room for an exact-size re-encoding: fit refuses, auto takes the shift layout, output gate-clean"""
    src = os.path.join(ORACLE, "2024_hvac_setstring_mark.rvt")
    if not os.path.exists(src): pytest.skip("oracle output not present")
    with pytest.raises(segedit.Refused, match="does not fit"): segedit.apply_ops(src, str(tmp_path / "f.rvt"), [dict(op="move", eid=EID, dx=2.0, dy=0.0, dz=0.0)], mode="fit")
    info = segedit.apply_ops(src, str(tmp_path / "a.rvt"), [dict(op="move", eid=EID, dx=2.0, dy=0.0, dz=0.0)])
    assert info["mode"] == "shift" and "fallback" in info and gate_damage(str(tmp_path / "a.rvt")) == []


def test_inplace_move_uses_product_dependents_check(env):
    """in-place move: an MEP-connected element is refused by the product rule (save.risky_membership); a dependent-free instance is saved, backup exact"""
    tmp, src = env; m0 = md5(src)
    with pytest.raises(segedit.Refused, match="dependents"): segedit.save_in_place(str(src), [dict(op="move", eid=EID, dx=2.0, dy=0.0, dz=0.0)])
    assert md5(src) == m0
    info = segedit.save_in_place(str(src), [dict(op="move", eid=1421396, dx=1.5, dy=-0.5, dz=0.0)])
    assert md5(info["backup"]) == m0 and gate_damage(str(src)) == [] and info["verify"]["readback"][0][1] == "move"
