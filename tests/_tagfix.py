"""helper for the wall-delete tests. Since the 'refuse deleting a tag host' rule (item 81) a wall that hosts tags cannot be deleted in the same save as its tags (the check reads the source file), so the tests first delete the tags in a separate save and cache that stripped copy (local, next to the sample)."""
import os, sys
for p in ('~/rvt-research', '~/rvt-research/edit-lab', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
def stripped(src, eid):
    out = os.path.join(os.path.dirname(src), 'notags%d_' % eid + os.path.basename(src))
    if os.path.exists(out): return out
    import rvtedit
    from rvtballet import edit
    tags = edit.tags_hosting(rvtedit.Edit(src), eid)
    if not tags: return src
    ops = [edit.validate_op({'op': 'delete', 'eid': t}) for t in tags]
    nb, _ = edit.apply_full(open(src, 'rb').read(), ops)
    open(out + '.part', 'wb').write(nb); os.replace(out + '.part', out)
    return out
