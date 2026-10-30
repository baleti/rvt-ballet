"""LIMITED verification for models too large for the element-level verify (SAVE AS only, explicit opt-in, never for overwrite).
Needs no reader and little memory (one stream at a time). It checks what can be checked without decoding elements:
  1. the output is a valid compound file with exactly the same streams as the source;
  2. every stream the edit did not touch is byte-identical;
  3. every stream that differs is a Partitions/* stream whose page layout parses, with the SAME number of gzip members;
  4. inside a differing partition at most `max_members` members have different decompressed bytes (the edit's footprint), all other members are byte-identical, and the bytes outside the members differ
     at most in trailing zero padding.
It does NOT prove that the changed members are the declared elements, nor that Revit accepts the file: it is a structural safety net, reported as such."""
import os, sys


class LightVerifyFailed(Exception):
    def __init__(self, msg, report=None): super().__init__(msg); self.report = report or {}


def _mods():
    from .edit import WL
    if WL not in sys.path: sys.path.insert(0, WL)
    import cfb, rvtw
    return cfb, rvtw


def light_verify(src_bytes, out_bytes, n_ops=1, max_members_per_op=4):
    cfb, rvtw = _mods()
    try: a = cfb.CFB(src_bytes).streams(); b = cfb.CFB(out_bytes).streams()
    except Exception as e: raise LightVerifyFailed('output is not a valid compound file (%s: %s)' % (type(e).__name__, e))
    if set(a) != set(b): raise LightVerifyFailed('stream set differs: %s' % sorted(set(a) ^ set(b))[:5], {'streams': sorted(set(a) ^ set(b))[:5]})
    diff = [k for k in a if a[k].data != b[k].data]
    bad = [k for k in diff if not k.startswith('Partitions/')]
    if bad: raise LightVerifyFailed('stream(s) that an edit must not touch changed: %s' % bad[:5], {'streams': bad[:5]})
    if len(diff) > max(1, n_ops): raise LightVerifyFailed('%d partition streams differ for %d edit(s)' % (len(diff), n_ops), {'streams': diff[:5]})
    report = {'streams': len(a), 'changed_streams': len(diff), 'changed_members': 0}
    for k in diff:
        try:
            sa, sb = rvtw.Stream(a[k].data), rvtw.Stream(b[k].data); pa, pb = bytes(sa.payload), bytes(sb.payload)
            ma = rvtw.members(pa, pa.find(rvtw.GZ)); mb = rvtw.members(pb, pb.find(rvtw.GZ))
        except Exception as e: raise LightVerifyFailed('%s does not parse as a paged gzip stream (%s: %s)' % (k, type(e).__name__, e))
        if len(ma) != len(mb): raise LightVerifyFailed('%s: member count %d -> %d' % (k, len(ma), len(mb)), {'stream': k})
        changed = 0
        for (p1, e1, _), (p2, e2, _) in zip(ma, mb):
            ra, _ = rvtw.read_member(pa, p1); rb, _ = rvtw.read_member(pb, p2)
            if ra != rb: changed += 1
        if changed > max_members_per_op * max(1, n_ops): raise LightVerifyFailed('%s: %d members changed (allowed %d for %d edit(s))' % (k, changed, max_members_per_op * max(1, n_ops), n_ops), {'stream': k, 'changed_members': changed})
        # bytes outside the members: identical up to trailing zero padding
        ta = pa[max(e for _, e, _ in ma):]; tb = pb[max(e for _, e, _ in mb):]
        if ta.rstrip(b'\0') != tb.rstrip(b'\0'): raise LightVerifyFailed('%s: data outside the gzip members changed' % k, {'stream': k})
        report['changed_members'] += changed
    report['note'] = 'LIMITED verification: structure and member footprint only, no element-level comparison'
    return report
