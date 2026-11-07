import os, sys, glob, time
sys.path.insert(0, '~/src/rvt-ballet')
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
from rvtballet import edit, save
sg = save._import()
for y in sys.argv[1:]:
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%s/*.rvt' % y)), key=os.path.getsize)
    if not fs: print(y, 'no sample'); continue
    f = fs[0]; buf = open(f, 'rb').read(); t0 = time.time()
    try:
        P = save._read_params(buf); hit = None
        for eid, p in P.items():
            p = p.get('params', p)
            ks = [k for k in p if k.endswith('|Double') and isinstance(p[k], float) and p[k] != 0]
            if ks and 'Type Id' not in p and 'Family Name' in p or (ks and 'Type Name' in p): hit = (eid, ks[0][:-7], p[ks[0]]); break
        if not hit: print(y, 'no type with Double param'); continue
        eid, nm, v = hit; op = edit.validate_op({'op': 'set_type_num', 'eid': eid, 'param': nm, 'value': v * 1.5 + 0.25})
        out = edit.apply_full(buf, [op])[0]; save._readback(buf, out, [op])
        print(y, 'OK', eid, nm, v, '->', op['value'], '%.0fs' % (time.time() - t0))
    except Exception as x: print(y, 'REFUSED/ERR', type(x).__name__, str(x)[:160])
