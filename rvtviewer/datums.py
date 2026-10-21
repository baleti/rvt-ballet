"""Levels, grids, rooms, views, sheets from decoded records (own extraction; names/ids as stored in the file)."""
import numpy as np
from .build_util import g

def _name_of(ctx, i):
    r = ctx.recs.get(i)
    if not r: return ''
    f = r['fields']
    return f.get('m_text') or f.get('m_viewName') or f.get('m_name') or ctx.par.get(i, {}).get('params', {}).get('Name') or ''

def rooms(ctx, lvl_names):
    out = []
    for e, r in ctx.recs.items():
        if r['class'] != 'RoomElem': continue
        f = r['fields']; ps = g(f, 'm_pParamValueSetAString', 'm_paramSet') or []
        vals = [p['m_value'] for p in ps if isinstance(p, dict)]
        kind = {-2000160: 'Room', -2003600: 'Space', -2003200: 'Area'}.get(ctx.catid(e), 'Room')
        lv = ctx.eid_int(f.get('m_levelId')) if 'm_levelId' in f else None
        if lv not in ctx.levels: lv = ctx.eid_int(f.get('m_assocLevelId'))
        pt = f.get('m_point'); bb = ctx.bbox(e)
        if (not pt or len(pt) != 3) and bb is not None: pt = ((bb[0] + bb[1]) / 2).tolist()
        out.append({'id': e, 'kind': kind, 'number': vals[0] if vals else '', 'name': vals[1] if len(vals) > 1 else '', 'level': lvl_names.get(lv, ''),
                    'pt': [float(x) * 0.3048 for x in pt] if pt else None})
    return sorted(out, key=lambda r: (r['kind'], str(r['number'])))

def phases(ctx):
    """ProjectPhase names in file order + the phase-created id of every element (index into the list, -1 unknown)"""
    names = []; ids = {}
    for e, r in sorted(ctx.recs.items()):
        if r['class'] == 'ProjectPhase': ids[e] = len(names); names.append(r['fields'].get('m_name') or 'Phase %d' % e)
    return names, ids

def _crop(ctx, f):
    """active crop region of a view (its Viewer record's bounded space: origin, basis, per-axis [max, min] offsets in ft) -> 4 world corners (m) of the
    crop rectangle in the view plane, or None when the crop is off (Revit then shows the whole model)"""
    vr = ctx.recs.get(ctx.eid_int(f.get('m_viewerId')) or -1)
    bs = (vr['fields'].get('m_boundedSpace') if vr else None) or {}
    try:
        act = bs.get('m_boundActive') or []
        if not (any(act[0]) and any(act[1])): return None
        O = np.array(bs['m_orig'], float); B = np.array(bs['m_basis'], float); b = bs['m_boundOffset']
        xs = sorted(float(x) for x in b[0][:2]); ys = sorted(float(y) for y in b[1][:2])
        if xs[1] - xs[0] < 1e-6 or ys[1] - ys[0] < 1e-6 or max(map(abs, xs + ys)) > 1e6: return None
        return [[round(float(c) * 0.3048, 4) for c in O + B[0] * x + B[1] * y] for x, y in ((xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1]))]
    except Exception:
        return None

def views_sheets(ctx):
    views = []; sheets = []; vp = {}
    for e, r in ctx.recs.items():
        c = r['class']; f = r['fields']
        if c == 'Viewport': vp[e] = ctx.eid_int(f.get('m_dbViewId'))
    for e, r in ctx.recs.items():
        c = r['class']; f = r['fields']
        if not c.startswith('DBView') or c == 'DBView': continue
        n = f.get('m_viewName')
        if n is None: continue
        if c == 'DBViewDrafting' and f.get('m_sheetNumber'):
            dr = ctx.recs.get(ctx.eid_int(f.get('m_dbDrawingId')) or -1)
            vids = [int(v) for v in ((dr['fields'].get('m_viewports') if dr else None) or f.get('m_sheetViewportElemIds') or [])]
            vs = [_name_of(ctx, vp[v]) for v in vids if v in vp and vp[v] in ctx.recs]
            sheets.append({'id': e, 'number': f.get('m_sheetNumber'), 'name': n, 'views': [x for x in vs if x], 'issued': f.get('m_issueDate') or '', 'drawnBy': f.get('m_drawnBy') or ''})
        else:
            v = {'id': e, 'name': n, 'kind': c[6:], 'template': bool(f.get('m_isTemplate')), 'scale': f.get('m_scale')}
            def m3(x):
                try: return [round(float(a) * 0.3048, 4) for a in x]
                except Exception: return None
            def d3(x):
                try: return [round(float(a), 5) for a in x]
                except Exception: return None
            if f.get('m_viewDir') is not None and not f.get('m_isTemplate'):
                v['origin'] = m3(f.get('m_origin')); v['dir'] = d3(f.get('m_viewDir')); v['up'] = d3(f.get('m_vertDir'))
                pl = g(f, 'm_pCutter', 'm_pPlane')
                if isinstance(pl, dict) and 'm_origin' in pl: v['cut'] = {'origin': m3(pl['m_origin']), 'normal': d3(np.cross(pl.get('m_xVec', [1, 0, 0]), pl.get('m_yVec', [0, 1, 0])).tolist())}
                if c == 'DBViewPlan':      # view range (ft): cut plane, view depth (bottom), top clip; "unlimited" is +-1e9
                    rg = {k: round(float(f[m]) * 0.3048, 4) for k, m in (('cut', 'm_cutPlaneElev'), ('top', 'm_topClipElev'), ('bottom', 'm_bottomClipElev')) if isinstance(f.get(m), (int, float)) and abs(f[m]) < 1e6}
                    if rg: v['range'] = rg
                cr = _crop(ctx, f)
                if cr: v['crop'] = cr
                if c == 'DBViewSection':      # Revit view family from DBViewSection.m_sectionViewType (0 section, 2 elevation, 3 detail / callout; checked on 2020 Residential): elevations are not cut (no cut fills / poche)
                    fam = {0: 'section', 2: 'elevation', 3: 'detail'}.get(f.get('m_sectionViewType'))
                    if fam: v['family'] = fam
                if c == 'DBViewSection':      # view depth: Viewer.m_boundedSpace z axis, far side offset in ft, when its far bound is active (m_boundActive[2][0])
                    try:
                        vr = ctx.recs.get(ctx.eid_int(f.get('m_viewerId')) or -1); bs = (vr['fields'].get('m_boundedSpace') if vr else None) or {}
                        dz = float(bs['m_boundOffset'][2][0]) * 0.3048
                        if (bs.get('m_boundActive') or [[], [], []])[2][0] and f.get('m_backClipping') != 0 and 0 < dz < 1e4: v['depth'] = round(dz, 4)
                    except Exception: pass
            views.append(v)
    # 3D views' section boxes: ModelClipBox.m_viewer3dId -> Viewer3d.m_dbViewId -> view; stored as origin + basis + per-axis [max, min] offsets (ft)
    byid = {v['id']: v for v in views}
    for e, r in ctx.recs.items():
        if r['class'] != 'ModelClipBox': continue
        try:
            bs = r['fields'].get('m_boundedSpace') or {}; act = bs.get('m_boundActive') or []
            v3 = ctx.recs.get(ctx.eid_int(r['fields'].get('m_viewer3dId')) or -1); v = byid.get(ctx.eid_int(v3['fields'].get('m_dbViewId'))) if v3 else None
            if v is None or not bs.get('m_isOn') or not all(any(a) for a in act[:3]): continue
            O = np.array(bs['m_orig'], float); B = np.array(bs['m_basis'], float); bo = bs['m_boundOffset']
            v['section_box'] = {'origin': [round(float(x) * 0.3048, 4) for x in O], 'basis': [[round(float(x), 6) for x in row] for row in B],
                                'ranges': [[round(float(min(o)) * 0.3048, 4), round(float(max(o)) * 0.3048, 4)] for o in bo[:3]]}
        except Exception:
            continue
    return sorted(views, key=lambda v: (v['kind'], v['name'])), sorted(sheets, key=lambda s: str(s['number']))
