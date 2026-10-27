"""Materials for the viewer: the reader's material/appearance tables (rvt_materials) condensed into a compact list, plus a procedural-texture class per material.
Colours, transparency, shininess/smoothness and the texture asset PATH come from the .rvt ('from file'); the texture bitmaps themselves are not stored in the .rvt, so the viewer
draws a built-in procedural texture of the matching class ('fallback'), scaled by the asset's real-world scale. The inspector says which is which."""
import os, re
from . import reader

TEX_CLASSES = ['none', 'brick', 'concrete', 'wood', 'stone', 'metal', 'glass', 'tile', 'plaster', 'grass', 'water', 'roof', 'insulation', 'siding', 'carpet']
_RULES = [   # (class, regex over name + class + category + texture path + schema)
    ('siding', r'siding|clapboard|weatherboard|lap board|cladding.*board'), ('roof', r'shingle|shake'), ('carpet', r'carpet|rug|fabric|textile|upholster'), ('glass', r'glass|glaz|window|mirror'), ('water', r'water|pool'), ('stone', r'stone|granite|marble|slate|limestone|sandstone'), ('brick', r'brick|masonry|cmu|block\b'), ('tile', r'tile|ceramic|porcelain|terrazzo|mosaic'),
    ('wood', r'wood|timber|oak|pine|maple|walnut|birch|cherry|lumber|plywood|hardwood|laminate|veneer|door'), ('stone', r'stone|granite|marble|slate|limestone|sandstone|gravel|paving|rock'),
    ('concrete', r'concrete|cement|screed|cast.?in|precast|footing'), ('metal', r'metal|steel|alumin|iron|copper|bronze|brass|zinc|chrome|stainless|galvan'),
    ('plaster', r'plaster|gypsum|drywall|paint|stucco|render|gwb|wallboard|finish'), ('grass', r'grass|lawn|turf|soil|earth|planting|vegetation|landscap|topsoil|sod'),
    ('roof', r'roof|shingle|asphalt|membrane|bitumen|thatch|slate roof'), ('insulation', r'insulation|batt|foam|rigid|vapor|air barrier'),
]


def classify(m):
    """-> procedural texture class for a material record of rvt_materials.material_table"""
    a = m.get('appearance') or {}
    tex = (m.get('texture') or {}).get('path') or ''
    hay = ' '.join(str(x) for x in (m.get('name'), m.get('class'), m.get('category'), tex, a.get('schema'), a.get('name')) if x).lower()
    sch = str(a.get('schema') or '').lower()
    if 'glazing' in sch or (m.get('transparency') or 0) >= 0.4 and re.search(r'glass|glaz|window', hay): return 'glass'
    for cls, rx in _RULES:
        if re.search(rx, hay): return cls
    if 'metal' in sch: return 'metal'
    if 'hardwood' in sch or 'wood' in sch: return 'wood'
    if 'concrete' in sch: return 'concrete'
    if 'masonry' in sch: return 'brick'
    if 'ceramic' in sch: return 'tile'
    if 'wallpaint' in sch: return 'plaster'
    return 'none'


UNIT_FT = {3: 1.0, 6: 1.0 / 12.0, 2: 1.0 / 30.48, 1: 1.0 / 304.8, 4: 3.28084}      # AProperty.m_unit of distances: 3 = feet, 6 = inches (seen in the corpus); 1/2/4 assumed mm/cm/m
TEX_LIB = os.environ.get('RVT_TEXTURE_LIB', os.path.expanduser('~/.cache/rvt-textures'))   # optional local copy of the Autodesk material library textures (never shipped)


def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o


def asset_extras(src):
    """{appearance asset id: {'thumb': PNG bytes (Revit's own material swatch stored in the file) or None, 'scale_ft': [x, y] (unit-converted texture_RealWorldScale of the
    diffuse texture), 'offset_ft': [x, y], 'angle_deg'}} read from the AppearanceAssetElem records (m_pThumbnail.m_compressedImage, AProperty.m_unit)"""
    reader._import(); import rvt_geometry as G
    out = {}
    def tex(a):
        """first connected bitmap asset of the diffuse property (else of any property) -> its unit-aware scale / offset / angle"""
        best = None
        prism = str(next((_ob(q).get('m_value') for q in (_ob(a).get('m_aAProperties') or []) if _ob(q).get('m_sName') == 'BaseSchema'), '')).startswith('Prism')
        for p in (_ob(a).get('m_aAProperties') or []):
            p = _ob(p)
            for c in (p.get('m_aConnected') or []):
                props = {_ob(q).get('m_sName'): _ob(q) for q in (_ob(c).get('m_aAProperties') or [])}
                if 'texture_RealWorldScaleX' not in props: continue
                def d(k):
                    q = props.get(k)
                    if not q or not isinstance(q.get('m_value'), (int, float)): return None
                    return float(q['m_value']) * (1.0 / 12.0 if (prism and q.get('m_unit') is None) else UNIT_FT.get(q.get('m_unit'), 1.0))      # Prism maps store no unit: inches (brick_running 32 x 30 = 12 courses)
                r = {'scale_ft': [d('texture_RealWorldScaleX'), d('texture_RealWorldScaleY')], 'offset_ft': [d('texture_RealWorldOffsetX') or 0.0, d('texture_RealWorldOffsetY') or 0.0],
                     'angle_deg': (props.get('texture_WAngle') or {}).get('m_value') or 0.0, 'prop': p.get('m_sName'),
                     'path': '|'.join(dict.fromkeys(x.replace('\\', '/') for x in str((props.get('unifiedbitmap_Bitmap') or {}).get('m_value') or '').split('|') if x)) or None}
                nm = str(p.get('m_sName') or ''); r['colour'] = nm.endswith(('diffuse', '_color', '_colour')) or nm in ('opaque_albedo', 'metal_f0')      # bump / pattern / cutout / reflectance maps are not colour images
                if nm in ('generic_diffuse', 'opaque_albedo'): return r
                if best is None or (r['colour'] and not best['colour']): best = r
        if best is not None and not best['colour']: best = dict(best, path=None)
        return best
    def bump(a):
        """the bump map of an appearance asset (generic_bump_map, concrete_bump_map, ...): bitmap path, its own unit-aware real-world scale / offset / angle, and the *_bump_amount"""
        props = {_ob(p).get('m_sName'): _ob(p) for p in (_ob(a).get('m_aAProperties') or [])}
        amt = next((float(q['m_value']) for k, q in props.items() if str(k).endswith('bump_amount') and isinstance(q.get('m_value'), (int, float))), None)
        for nm, p in props.items():
            if not str(nm).endswith('bump_map'): continue
            for c in (p.get('m_aConnected') or []):
                cp = {_ob(q).get('m_sName'): _ob(q) for q in (_ob(c).get('m_aAProperties') or [])}
                path = '|'.join(dict.fromkeys(x.replace('\\', '/') for x in str((cp.get('unifiedbitmap_Bitmap') or {}).get('m_value') or '').split('|') if x))
                if not path: continue
                def d(k):
                    q = cp.get(k)
                    return float(q['m_value']) * UNIT_FT.get(q.get('m_unit'), 1.0) if q and isinstance(q.get('m_value'), (int, float)) else None
                return {'bump_path': path, 'bump_scale_ft': [d('texture_RealWorldScaleX'), d('texture_RealWorldScaleY')], 'bump_offset_ft': [d('texture_RealWorldOffsetX') or 0.0, d('texture_RealWorldOffsetY') or 0.0],
                        'bump_angle': (cp.get('texture_WAngle') or {}).get('m_value') or 0.0, 'bump_amount': amt}
        return None
    for eid, r in G.get_ctx(src).recs.items():
        if r['class'] != 'AppearanceAssetElem': continue
        f = _ob(r['fields']); th = _ob(f.get('m_pThumbnail')) if f.get('m_pThumbnail') is not None else None
        png = th.get('m_compressedImage') if isinstance(th, dict) else None
        try: t = tex(_ob(f.get('m_pAppearanceAsset') or {}).get('m_Asset') or {})
        except Exception: t = None
        try: bm = bump(_ob(f.get('m_pAppearanceAsset') or {}).get('m_Asset') or {})
        except Exception: bm = None
        out[eid] = {'thumb': bytes(png) if isinstance(png, (bytes, bytearray)) and png[:4] == b'\x89PNG' else None, **(t or {}), **(bm or {})}
    return out


import functools


@functools.lru_cache(maxsize=512)
def flat_swatch(png):
    """True when Revit's swatch is a full-frame texture (grass, gravel, asphalt, tiles) rather than a rendered sphere / cube / wall: usable as a tileable texture"""
    try:
        import io, numpy as np
        from PIL import Image
        a = np.asarray(Image.open(io.BytesIO(png)).convert('RGB')).astype(float)
        h, w = a.shape[:2]
        if h < 32 or w < 32: return False
        b = a[:h // 4 * 4, :w // 4 * 4].reshape(4, h // 4, 4, w // 4, 3).mean(axis=(1, 3))
        return float(np.abs(b - a.mean(axis=(0, 1))).max()) < 12.0
    except Exception: return False


def swatch_mean(png):
    try:
        import io, numpy as np
        from PIL import Image
        return [int(x) for x in np.asarray(Image.open(io.BytesIO(png)).convert('RGB')).reshape(-1, 3).mean(0)]
    except Exception: return None


_LIB_INDEX = {}
def library_texture(path):
    """absolute file of a texture asset path in the local material library copy (case-insensitive, any of the '|' alternatives), or None"""
    if not path or not os.path.isdir(TEX_LIB): return None
    if TEX_LIB not in _LIB_INDEX:
        idx = {}
        for dp, _, fs in os.walk(TEX_LIB):
            for fn in fs: idx.setdefault(os.path.relpath(os.path.join(dp, fn), TEX_LIB).replace('\\', '/').lower(), os.path.join(dp, fn)); idx.setdefault(fn.lower(), os.path.join(dp, fn))
        _LIB_INDEX[TEX_LIB] = idx
    idx = _LIB_INDEX[TEX_LIB]
    for p in str(path).split('|'):
        p = p.replace('\\', '/').strip().lower()
        if p in idx: return idx[p]
        if os.path.basename(p) in idx: return idx[os.path.basename(p)]
    return None


def write_images(outdir, mats, log=print):
    """writes tex/<k>.png (texture tile, 256 px: library bitmap or flat swatch) and swatch/<k>.png (Revit's swatch) for material list position k; sets rec['swatch'], rec['tex_img']"""
    try:
        import io
        from PIL import Image
    except Exception as ex: log('no PIL, material images skipped: %r' % ex); return
    for d in ('swatch', 'tex', 'bump'): os.makedirs(os.path.join(outdir, d), exist_ok=True)
    nlib = nsw = nb = 0
    for k, m in enumerate(mats['list']):
        png = mats.get('thumbs', {}).get(m['id'])
        if png:
            open(os.path.join(outdir, 'swatch', '%d.png' % k), 'wb').write(png); m['swatch'] = True
        lib = library_texture(m.get('tex_path')) if m.get('tex_colour') else None
        try:
            if lib:
                Image.open(lib).convert('RGB').resize((256, 256), Image.LANCZOS).save(os.path.join(outdir, 'tex', '%d.png' % k), compress_level=1); m['tex_img'] = 'library'; nlib += 1
                m['texture_source'] = 'bitmap ' + str(m.get('tex_path')) + ' from the local Autodesk material library copy (not stored in the .rvt), real-world size ' + _fmt_ft(m.get('tex_scale_ft'))
            elif png and flat_swatch(png):
                q = Image.open(io.BytesIO(png)).convert('RGB').resize((128, 128), Image.BICUBIC); t = Image.new('RGB', (256, 256))       # 2 x 2 mirrored: a seamless tile from a non-tileable swatch
                t.paste(q, (0, 0)); t.paste(q.transpose(Image.FLIP_LEFT_RIGHT), (128, 0)); t.paste(q.transpose(Image.FLIP_TOP_BOTTOM), (0, 128)); t.paste(q.transpose(Image.ROTATE_180), (128, 128))
                t.save(os.path.join(outdir, 'tex', '%d.png' % k), compress_level=1); m['tex_img'] = 'swatch'; m['tex_tile_mul'] = 2; nsw += 1
                m['texture_source'] = "Revit's own swatch image stored in the file, tiled at the asset's real-world size " + _fmt_ft(m.get('tex_scale_ft')) + ' (low resolution; the bitmap ' + str(m.get('tex_path')) + ' is not in the .rvt)'
        except Exception as ex: log('texture image %s: %r' % (m.get('name'), ex))
        blib = library_texture(m.get('bump_path')) if m.get('bump_path') else None
        if blib:                                             # bump (height) map: grey 256 px tile, the shader perturbs the normal with its screen-space gradient
            try: Image.open(blib).convert('L').resize((256, 256), Image.LANCZOS).save(os.path.join(outdir, 'bump', '%d.png' % k)); m['bump_img'] = True; nb += 1; m['texture_source'] = (m.get('texture_source') or '') + '; bump map ' + str(m['bump_path']).split('|')[0] + ' (local library), amount ' + str(m.get('bump_amount') if m.get('bump_amount') is not None else 1)
            except Exception as ex: log('bump image %s: %r' % (m.get('name'), ex))
    log('material images: %d swatches, %d library bitmaps, %d swatch textures, %d bump maps' % (sum(1 for m in mats['list'] if m.get('swatch')), nlib, nsw, nb))


def _fmt_ft(s):
    if not s or not s[0]: return '(unknown)'
    return ' x '.join('%.3g ft' % x for x in s if x)


PRISM_COLOUR = ('opaque_albedo', 'layered_diffuse', 'metal_f0', 'transparent_color', 'glazing_transmission_color')
def prism_colour(a):
    """colour of a Prism (Advanced) appearance asset, 0..255 RGB, or None"""
    pr = (a or {}).get('properties') or {}
    for k in PRISM_COLOUR:
        v = pr.get(k)
        if isinstance(v, (list, tuple)) and len(v) >= 3 and all(isinstance(x, (int, float)) for x in v[:3]): return [round(float(x) * 255) for x in v[:3]]
    return None


def load(src, log=print):
    """-> {'list': [record], 'index': {revit material id: position}} ; record: id, name, class, category, rgb [0..1], alpha, smooth, shin, metal, tex_class, tex_path, tex_scale_ft [x, y], tex_angle, schema, source flags"""
    try:
        reader._import(); import rvt_materials as RM
        mt = RM.material_table(src)
    except Exception as ex:
        log('materials unavailable: %r' % ex); return {'list': [], 'index': {}}
    try: ext = asset_extras(src)
    except Exception as ex: log('appearance extras unavailable: %r' % ex); ext = {}
    try: fpat = RM.fill_patterns(src)
    except Exception as ex: log('fill patterns unavailable: %r' % ex); fpat = {}
    def gfx(p):          # material graphics pattern (surface / cut): None when the material has none
        if not p or p.get('id') is None: return None
        return {'id': p['id'], 'name': (fpat.get(p['id']) or {}).get('name'), 'color': p.get('color'), 'background': p.get('background_color') if p.get('background_id') is not None else None,
                'target': (fpat.get(p['id']) or {}).get('target'), 'grids': [{k: ([round(x, 6) for x in v] if isinstance(v, list) else round(v, 6)) for k, v in g.items()} for g in ((fpat.get(p['id']) or {}).get('grids') or [])[:64]]}
    out = []; index = {}; thumbs = {}
    for mid, m in mt.items():
        ax = ext.get(m.get('appearance_asset_id')) or {}
        if ax.get('thumb'): thumbs[mid] = ax['thumb']
        a = m.get('appearance') or {}; tex = m.get('texture') or {}
        col = a.get('diffuse') or prism_colour(a) or m.get('color') or [180, 180, 180]
        if m.get('use_render_appearance') is False or not (a.get('diffuse') or prism_colour(a)): col = m.get('color') or col
        csrc = 'from file (appearance diffuse)' if a.get('diffuse') else ('from file (advanced appearance colour)' if prism_colour(a) else 'from file (material colour)')
        if ax.get('colour') and ax.get('path'):          # the diffuse is a bitmap (its colour value is a placeholder, often white): average of a flat swatch, else the material's shading colour
            mc = swatch_mean(ax['thumb']) if ax.get('thumb') and flat_swatch(ax['thumb']) else None
            if mc: col = mc; csrc = "from file (average of Revit's swatch; the diffuse is a bitmap)"
            elif m.get('color'): col = m['color']; csrc = 'from file (material shading colour; the diffuse is a bitmap)'
        tr = m.get('transparency') or 0.0
        cls = classify(m)
        scale = [v for v in (ax.get('scale_ft') or []) if v] or [x for x in (tex.get('scale') or []) if x]
        rec = {'id': mid, 'name': m.get('name') or str(mid), 'class': m.get('class'), 'category': m.get('category'), 'rgb': [round(c / 255.0, 3) for c in col[:3]], 'alpha': round(1.0 - float(tr), 3),
               'smooth': m.get('smoothness'), 'shin': m.get('shininess'), 'metal': bool(a.get('metal')), 'glossiness': a.get('glossiness'), 'schema': a.get('schema'), 'asset': a.get('name'),
               'tex_class': cls, 'tex_path': (ax.get('path') if 'prop' in ax else tex.get('path')), 'tex_prop': ax.get('prop'), 'tex_colour': bool(ax.get('colour') and ax.get('path')), 'tex_scale_ft': scale[:2] or None, 'tex_angle': ax.get('angle_deg', tex.get('angle')), 'tex_offset_ft': ax.get('offset_ft'),
               'surface_pattern': gfx(m.get('surface_pattern')), 'cut_pattern': gfx(m.get('cut_pattern')),
               'color_source': csrc, **{k: ax[k] for k in ('bump_path', 'bump_scale_ft', 'bump_offset_ft', 'bump_angle', 'bump_amount') if k in ax},
               'texture_source': ('texture asset ' + str(tex.get('path')) + ' is not stored in the .rvt: built-in procedural "' + cls + '" (fallback)') if tex.get('path') and cls != 'none' else
                                 ('no texture asset: procedural "' + cls + '" chosen from the material name (fallback)' if cls != 'none' else 'no texture')}
        index[mid] = len(out); out.append(rec)
    return {'list': out, 'index': index, 'thumbs': thumbs}


# per-parameter fallbacks: element/type parameters that name a material
MATERIAL_PARAMS = ('Material', 'Structural Material', 'Frame Material', 'Finish', 'Glass', 'Material for Model Behavior', 'Cladding Material', 'Panel Material', 'Mullion Material')
