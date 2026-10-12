"""Materials for the viewer: the reader's material/appearance tables (rvt_materials) condensed into a compact list, plus a procedural-texture class per material.
Colours, transparency, shininess/smoothness and the texture asset PATH come from the .rvt ('from file'); the texture bitmaps themselves are not stored in the .rvt, so the viewer
draws a built-in procedural texture of the matching class ('fallback'), scaled by the asset's real-world scale. The inspector says which is which."""
import re
from . import reader

TEX_CLASSES = ['none', 'brick', 'concrete', 'wood', 'stone', 'metal', 'glass', 'tile', 'plaster', 'grass', 'water', 'roof', 'insulation']
_RULES = [   # (class, regex over name + class + category + texture path + schema)
    ('glass', r'glass|glaz|window|mirror'), ('water', r'water|pool'), ('stone', r'stone|granite|marble|slate|limestone|sandstone'), ('brick', r'brick|masonry|cmu|block\b'), ('tile', r'tile|ceramic|porcelain|terrazzo|mosaic'),
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


def load(src, log=print):
    """-> {'list': [record], 'index': {revit material id: position}} ; record: id, name, class, category, rgb [0..1], alpha, smooth, shin, metal, tex_class, tex_path, tex_scale_ft [x, y], tex_angle, schema, source flags"""
    try:
        reader._import(); import rvt_materials as RM
        mt = RM.material_table(src)
    except Exception as ex:
        log('materials unavailable: %r' % ex); return {'list': [], 'index': {}}
    out = []; index = {}
    for mid, m in mt.items():
        a = m.get('appearance') or {}; tex = m.get('texture') or {}
        col = a.get('diffuse') or m.get('color') or [180, 180, 180]
        if m.get('use_render_appearance') is False or not a.get('diffuse'): col = m.get('color') or col
        tr = m.get('transparency') or 0.0
        cls = classify(m)
        scale = [x for x in (tex.get('scale') or []) if x]
        rec = {'id': mid, 'name': m.get('name') or str(mid), 'class': m.get('class'), 'category': m.get('category'), 'rgb': [round(c / 255.0, 3) for c in col[:3]], 'alpha': round(1.0 - float(tr), 3),
               'smooth': m.get('smoothness'), 'shin': m.get('shininess'), 'metal': bool(a.get('metal')), 'glossiness': a.get('glossiness'), 'schema': a.get('schema'), 'asset': a.get('name'),
               'tex_class': cls, 'tex_path': tex.get('path'), 'tex_scale_ft': scale[:2] or None, 'tex_angle': tex.get('angle'),
               'color_source': 'from file (appearance diffuse)' if a.get('diffuse') else 'from file (material colour)',
               'texture_source': ('texture asset ' + str(tex.get('path')) + ' is not stored in the .rvt: built-in procedural "' + cls + '" (fallback)') if tex.get('path') and cls != 'none' else
                                 ('no texture asset: procedural "' + cls + '" chosen from the material name (fallback)' if cls != 'none' else 'no texture')}
        index[mid] = len(out); out.append(rec)
    return {'list': out, 'index': index}


# per-parameter fallbacks: element/type parameters that name a material
MATERIAL_PARAMS = ('Material', 'Structural Material', 'Frame Material', 'Finish', 'Glass', 'Material for Model Behavior', 'Cladding Material', 'Panel Material', 'Mullion Material')
