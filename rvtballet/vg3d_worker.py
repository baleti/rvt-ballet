"""one-shot: python vg3d_worker.py FILE.rvt VIEWID  (run with the rvt-sheets python) -> JSON on stdout: the resolved graphics of a view, compact, for the 3D hidden-line style.
{view, kind, hidden: [element ids not drawn in the view], els: {eid: [fillR, fillG, fillB, opacity 0..1, lineR, lineG, lineB, line weight mm, halftone, pattern id or -1]}}  (only elements with a non-default value)"""
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/src/rvt-sheets'))
from rvtsheets.decode import Decoder
from rvtsheets.vg.resolve import resolve_view

dec = Decoder(sys.argv[1]); doc = dec.doc(); vid = int(sys.argv[2])
from rvtsheets.visibility import Visibility
vis = Visibility(dec, doc)
rep = resolve_view(dec, doc, vid, vis=vis, explain=True)
els = {}
for k, e in rep['elements'].items():
    o = e.get('overrides') or {}; p = e.get('proj') or {}
    fill = o.get('surf_fg_color'); tr = e.get('transparency') or 0
    lc = p.get('rgb') or [0, 0, 0]; w = p.get('w') or 0.18
    if fill or tr or lc != [0, 0, 0] or w > 0.2 or e.get('halftone'):
        els[k] = [*(fill or [255, 255, 255]), round(1 - tr / 100, 3), *lc, w, 1 if e.get('halftone') else 0, o.get('surf_fg_pattern', -1) if fill else -1]
# view-range exclusions of the sheets visibility engine (plans / sections / elevations only): elements outside the view volume, above the cut, below the range bottom ...
RANGE = ('outside_view_volume', 'mesh_outside_view_volume', 'wholly_above_cut', 'origin_outside_view', 'stair_above_cut', 'footing_touches_range_bottom', 'nonstructural_wall_in_structural_view')
rng = []
if rep['kind'] in ('plan', 'section', 'elevation', 'Plan', 'Section'):
    shown_, why_ = vis.elements(vid, explain=True)
    rng = [int(k) for k, w in why_.items() if w in RANGE]
json.dump({'view': rep['name'], 'kind': rep['kind'], 'hidden': [int(k) for k in rep.get('excluded_ids', {})], 'range_hidden': rng, 'els': els}, sys.stdout)
