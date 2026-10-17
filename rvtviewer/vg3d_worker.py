"""one-shot: python vg3d_worker.py FILE.rvt VIEWID  (run with the rvt-sheets python) -> JSON on stdout: the resolved graphics of a view, compact, for the 3D hidden-line style.
{view, kind, hidden: [element ids not drawn in the view], els: {eid: [fillR, fillG, fillB, opacity 0..1, lineR, lineG, lineB, line weight mm, halftone, pattern id or -1]}}  (only elements with a non-default value)"""
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/src/rvt-sheets'))
from rvtsheets.decode import Decoder
from rvtsheets.vg.resolve import resolve_view

dec = Decoder(sys.argv[1]); doc = dec.doc(); vid = int(sys.argv[2])
rep = resolve_view(dec, doc, vid, explain=True)
els = {}
for k, e in rep['elements'].items():
    o = e.get('overrides') or {}; p = e.get('proj') or {}
    fill = o.get('surf_fg_color'); tr = e.get('transparency') or 0
    lc = p.get('rgb') or [0, 0, 0]; w = p.get('w') or 0.18
    if fill or tr or lc != [0, 0, 0] or w > 0.2 or e.get('halftone'):
        els[k] = [*(fill or [255, 255, 255]), round(1 - tr / 100, 3), *lc, w, 1 if e.get('halftone') else 0, o.get('surf_fg_pattern', -1) if fill else -1]
json.dump({'view': rep['name'], 'kind': rep['kind'], 'hidden': [int(k) for k in rep.get('excluded_ids', {})], 'els': els}, sys.stdout)
