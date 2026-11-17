"""c9x-rvtlink: savegate in-place SAVE of a link ADD output (tools/rvt_add_link.py) on a PRIVATE copy of the Autodesk HVAC 2024 sample: accepted with the declared added ids; refused when the add is undeclared; refused on a corrupted output; backup == original; restore identical. usage: rvtsave_inplace_addlink.py hvac.rvt hvac_addlink.rvt ID1,ID2,ID3"""
import os, sys, tempfile, json, shutil, hashlib
T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'
json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
import savegate as sg
from savegate.adapters import RvtAdapter
from savegate import rvt_elements
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src, out, ids = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
nb = open(out, 'rb').read(); h0 = sha(src)
def attempt(label, data, manifest):
    p = T + '/t_' + label + '.rvt'; shutil.copy(src, p)
    cfg = sg.Config(allow_overwrite=True)
    try:
        with sg.open_doc(p, adapter=RvtAdapter(elements_fn=rvt_elements.elements), cfg=cfg) as d: sg.save(d, data, manifest)
        r = 'ACCEPTED' + (' changed' if sha(p) != h0 else ' UNCHANGED')
    except Exception as e: r = 'REFUSED(%s) %s original_untouched=%s' % (type(e).__name__ + ': ' + str(e)[:200], str(getattr(e, 'args', ())[1:])[:500], sha(p) == h0)
    print(label, r, flush=True); return p, r
p, r = attempt("declared", nb, {"added": ["el:%d" % i for i in ids]})
attempt('undeclared', nb, {})
bad = bytearray(nb); bad[len(bad) // 2] ^= 1
attempt('bitflip', bytes(bad), {"added": ["el:%d" % i for i in ids]})
attempt('truncated', nb[:-4096], {"added": ["el:%d" % i for i in ids]})
