#!/usr/bin/env python3
"""rvt_astring_create_proto.py SRC.rvt DST.rvt EID NAME VALUE : PROTOTYPE (not wired into edit.py, refused by the product) of Revit's 'create a never-set string parameter' (witness c4xcm1/cm2, Structural 2024: 24 B record growth).
Layout: Element.m_pParamValueSetAString null(4 B 00000000) -> ffffffff + u16 tag (tag = the one value shared by all elements of the file); a new object is inserted after the Double/Int set objects (before the ElementId one; order Double, Int, AString, ElementId): u32 count=1, u64 param id (negative BuiltInParameter id sign-extended), u32 nchars, UTF-16LE text. Autodesk samples / synthetic only; offline."""
import sys, os, struct, collections
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import rvtedit, rvt_xcache
BIP = {'Comments': -1010106}

def file_tag(src):
    c = collections.Counter()
    for k, r in rvt_xcache.get_x(src)['recs'].items():
        v = (r.get('fields') or {}).get('m_pParamValueSetAString')
        if isinstance(v, dict) and v.get('handle') == 4294967295 and 'ptr' in v: c[v['ptr']] += 1
    if len(c) != 1: raise SystemExit('refused: %d distinct AString-set tags in the file (need exactly 1): %s' % (len(c), dict(c)))
    return next(iter(c))

def main(src, dst, eid, name, value):
    eid = int(eid); tag = file_tag(src); ed = rvtedit.Edit(src); log = ed.g.e.trace(eid)[3]
    ptr = [l for l in log if l[1] == 'Element.m_pParamValueSetAString']
    if len(ptr) != 1 or ed.g.bj[ptr[0][2]:ptr[0][3]] != b'\0\0\0\0': raise SystemExit('refused: element already has (or lacks) the AString set pointer')
    sets = {l[1][len('ParamValueSet'):-len('.m_paramSet')]: l for l in log if l[1].startswith('ParamValueSet') and l[1].endswith('.m_paramSet')}
    # measured on 44 elements with 3+ sets (Structural 2024): serialisation order is Double, Int, AString, ElementId
    before = [sets[n] for n in ('Double', 'Int') if n in sets]
    if before: at = max(l[3] for l in before)
    elif 'ElementId' in sets: at = sets['ElementId'][2]
    else: raise SystemExit('refused: no Double/Int/ElementId ParamValueSet object to anchor the insertion')
    body = struct.pack('<I', 1) + struct.pack('<q', BIP[name]) + struct.pack('<I', len(value)) + value.encode('utf-16le')
    ed._rec_edit(eid, [(ptr[0][2], 4, b'\xff\xff\xff\xff' + struct.pack('<H', tag)), (at, 0, body)])
    ed.save(dst); print('saved', dst, 'tag', tag, 'insert at', at, 'bytes', len(body) + 2)

if __name__ == '__main__': main(*sys.argv[1:6])
