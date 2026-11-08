"""Delete must drop the deleted id from every Global/Latest id-list (count-1, 8 bytes out), like Revit's own Delete (c4x-rvtdiff, ~/c2x-diff/del1).
Synthetic raw bytes only; skipped when the write-lab (genlib2) is not installed."""
import os, struct, sys, pytest
WL = os.path.expanduser(os.environ.get('RVTBALLET_WRITELAB', '~/rvt-research/write-lab'))
sys.path.insert(0, WL)
genlib2 = pytest.importorskip('genlib2')
if not hasattr(genlib2, 'registry_remove'): pytest.skip('registry_remove missing', allow_module_level=True)

def lst(ids): return struct.pack('<I', len(ids)) + b''.join(struct.pack('<Q', i) for i in ids)

def test_remove_from_every_list_and_leave_others():
    a, b = [10, 20, 30, 40], [5, 20, 99]
    raw = b'HEAD' + lst(a) + b'MID_' + lst(b) + b'TAIL'
    known = set(a) | set(b)
    out = genlib2.apply_ops(raw, genlib2.registry_remove(raw, {20}, known))
    assert out == b'HEAD' + lst([10, 30, 40]) + b'MID_' + lst([5, 99]) + b'TAIL'

def test_nothing_to_remove_is_identity():
    raw = b'HEAD' + lst([1, 2, 3]) + b'TAIL'
    assert genlib2.apply_ops(raw, genlib2.registry_remove(raw, {7}, {1, 2, 3})) == raw
