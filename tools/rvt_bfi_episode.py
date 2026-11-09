#!/usr/bin/env python3
"""rvt_bfi_episode.py: offline model of Revit's BasicFileInfo change on a save, derived from 28 Revit-made base->after pairs (Autodesk samples).
bfi_next(x, new_guid): (1) every occurrence of the document GUID (36-char UTF-16 text) is replaced by new_guid; (2) the u32 save counter after the
'ENU' locale string +1; (3) the same count as decimal text at three places (+1; same digit count only, a 9->10 carry is refused).
Self-test: python3 rvt_bfi_episode.py BASE.rvt AFTER.rvt. Offline model only; not wired into any save path."""
import re, struct, sys
GUID = re.compile(rb'(?:[0-9a-f]\x00){8}-\x00(?:(?:[0-9a-f]\x00){4}-\x00){3}(?:[0-9a-f]\x00){12}')
def bfi_next(x, new_guids):
    """new_guids: list of fresh GUID strings, one per DISTINCT old GUID in order of first appearance (Revit has 2: 8 occurrences, 2 distinct)."""
    x = bytes(x)
    x = bytes(x); order = []
    for m in GUID.finditer(x):
        if m.group(0) not in order: order.append(m.group(0))
    assert len(order) == len(new_guids), 'distinct GUIDs %d != %d new' % (len(order), len(new_guids))
    y = x
    for g, n in zip(order, new_guids): y = y.replace(g, n.encode('utf-16le'))
    docs = order
    i = y.find(b'E\x00N\x00U\x00')      # strings here are length-prefixed and NOT 2-aligned
    assert i >= 0, 'no locale marker'
    j = i + 7
    y = bytearray(y); n = struct.unpack_from('<I', y, j)[0]; struct.pack_into('<I', y, j, n + 1)
    # the save count n also appears as decimal text: after the length marker 02 00 00 00 (2-char string), after 'latest: ' and after 'Increments: '
    txt = str(n).encode('utf-16le'); nxt = str(n + 1).encode('utf-16le')
    if len(txt) != len(nxt): raise ValueError('save-count digit carry changes the string length; refused')
    ys = bytes(y); cnt = 0
    for pre in (b'\x02\x00\x00\x00', 'latest: '.encode('utf-16le'), 'Increments: '.encode('utf-16le')):
        k = ys.find(pre + txt)
        assert k >= 0, 'save-count text not found after %r' % pre
        ys = ys[:k+len(pre)] + nxt + ys[k+len(pre)+len(txt):]; cnt += 1
    y = bytearray(ys)
    return bytes(y), docs
if __name__ == '__main__':
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import adiff
    a, b = sys.argv[1:3]
    x = adiff.graw(a, 'BasicFileInfo'); y = adiff.graw(b, 'BasicFileInfo')
    y = y.replace('_after'.encode('utf-16le'), '_base'.encode('utf-16le'))
    new = []
    for m in GUID.finditer(y):
        if m.group(0).decode('utf-16le') not in new: new.append(m.group(0).decode('utf-16le'))
    p, old = bfi_next(x, new)
    df = [i for i in range(len(y)) if p[i] != y[i]]
    print('EXACT' if not df else 'MISMATCH', len(p), len(y), df[:10])
