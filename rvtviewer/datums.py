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
            views.append(v)
    return sorted(views, key=lambda v: (v['kind'], v['name'])), sorted(sheets, key=lambda s: str(s['number']))
