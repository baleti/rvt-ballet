"""Edit model for SAVE: a per-model list of ops replayed on the loaded bytes with the write-lab Editor (rvt-research/write-lab/wledit.py).
Ops: {'op': 'set_string', 'eid': int, 'field': 'ParamValueAString.m_value' (default), 'value': str, 'match': optional old text}.
The manifest handed to savegate declares exactly the edited elements ('el:<id>' keys), so verify fails if anything else changed."""
import os, sys, tempfile

WL = os.path.expanduser(os.environ.get('RVTBALLET_WRITELAB', '~/rvt-research/write-lab'))
EL = os.path.expanduser(os.environ.get('RVTBALLET_EDITLAB', '~/rvt-research/edit-lab'))      # rvtedit.Edit (rvtedit2): same ops plus numeric params, dependents, delete, move
BACKEND = lambda: os.environ.get('RVTBALLET_EDIT_BACKEND', 'wledit')
DEFAULT_FIELD = 'ParamValueAString.m_value'
FIELDS = ('ParamValueAString.m_value', 'DatumPlane.m_text', 'DBView.m_viewName', 'SymbolInfo.m_name')   # string fields validated in write-lab (e3/e4)


class EditError(Exception): pass


def _pid_for(name):
    """parameter id for a built-in parameter name via the reader's PNAMES table; ambiguous or unknown names raise"""
    rr = os.path.expanduser('~/rvt-research')
    if rr not in sys.path: sys.path.insert(0, rr)
    try: import rvt_params
    except ImportError as e: raise EditError('editing by parameter name needs the reader (rvt_params from ~/rvt-research): %s' % e)
    ids = [int(k) for k, v in rvt_params.PNAMES.items() if v == name]
    if not ids: raise EditError('unknown parameter name %r (not in the reader\'s built-in table)' % name)
    return ids          # several categories can share a name: the one stored on the element is chosen when the op is applied


DERIVED_NUM = frozenset(['Unit weight'] + [a + ' ' + b for a in ('Young modulus', 'Poisson ratio', 'Shear modulus', 'Thermal expansion coefficient') for b in 'XYZ'])   # rvt_params.py: placeholder 0.0 on materials, Unit weight derived from Density on property sets (measured 2024/2026 e1_level: 23/23 such edits accepted then refused VerifyFailed)


def _param_spec(op):
    """(pid, candidate pids) of a parameter addressed by id or by NAME (resolved against the element when the op is applied)"""
    pid = op.get('pid')
    if pid is None: return None, _pid_for(op.get('param') or '')
    if not isinstance(pid, int) or isinstance(pid, bool): raise EditError('pid must be an integer')
    return pid, None


def _check_text(v):
    """NUL / length, and no characters beyond the BMP: a surrogate pair in a by-name string parameter was written without error and the gate accepted the output, but the element's parameter list then reads back truncated
    (13 of 26 parameters, edited one unreadable; c3x-rvtmatrix 2026-10-30, 2024 Construction template, rvtedit backend). Refused until the writer encoding is proven."""
    if '\0' in v or len(v) > 4096: raise EditError('value must not contain NUL and must be at most 4096 characters')
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in v): raise EditError('unpaired surrogate characters cannot be encoded; nothing was changed')
    if any(ord(ch) > 0xFFFF for ch in v): raise EditError('characters outside the Basic Multilingual Plane (emoji, rare CJK) are not supported in values yet; nothing was changed')


_OP_KEYS = {'set_string': {'op', 'eid', 'param', 'value', 'match', 'field', 'pid', 'pids', 'kind', 'expect'}, 'move': {'op', 'eid', 'dx', 'dy', 'dz'}, 'set_num': {'op', 'eid', 'param', 'pid', 'pids', 'value', 'kind'}, 'delete': {'op', 'eid'}, 'rotate': {'op', 'eid', 'deg'}, 'change_type': {'op', 'eid', 'type_eid'}, 'set_type_num': {'op', 'eid', 'param', 'pid', 'value'}, 'set_type_eid': {'op', 'eid', 'pid', 'target'}, 'set_type_yesno': {'op', 'eid', 'pid', 'value'}, 'set_type_material': {'op', 'eid', 'target'}, 'set_link_path': {'op', 'eid', 'value'}, 'set_link_load': {'op', 'eid', 'value'}, 'set_link_override': {'op', 'eid', 'link', 'linked_view'}, 'set_room_bounding': {'op', 'eid', 'value'}}      # strict key sets only for ops whose optional keys are safety guards


# VM-measured (c6x-rvtwrite, 2024 and 2025 Snowdon HVAC): writing the stored ParamValueInt of these does not change what the Revit API reports
# Int parameters that are choice lists: allowed range (inclusive), VM-measured with the Revit API display name (blank = invalid): Detail Level 1..3 valid, 4 blank (0 not measured, refused);
# Mullion Family General Shape 0..5 valid (6 blank); Tangent Joins 0 and 2 valid, 3 blank (1 assumed valid between them)
ENUM_INT_RANGE = {'Detail Level': (1, 3), 'Mullion Family General Shape': (0, 5), 'Tangent Joins': (0, 2)}


def _discipline_ok(v):
    """Discipline is a bit-flag choice: values seen in the Autodesk samples are 1, 2, 4, 8, 16 and 4095; Revit 2024 and 2026 show 3 and 5 with a blank name (VM readback), i.e. not a valid choice"""
    return v == 4095 or (v > 0 and v & (v - 1) == 0)


# material Class / Behavior: the reader shows the material asset's value, the stored ParamValueInt is a different field, so the edit never reads back (save-time read-back refuses it with 422 'unchanged by the edit'); refuse at /edit instead
READBACK_NEVER_MATCHES_INT = {'Class', 'Behavior'}
REVIT_IGNORES_STORED_INT = {'Return Airflow', 'Power Load Units', 'Lighting Load Units'}


def validate_op(op):
    if not isinstance(op, dict) or op.get('op') not in ('set_string', 'set_num', 'delete', 'move', 'rotate', 'change_type', 'set_link_override', 'set_type_num', 'set_type_eid', 'set_type_yesno', 'set_type_material', 'set_link_path', 'set_link_load', 'set_room_bounding'): raise EditError('unsupported edit op (supported: set_string, set_num, delete, move, rotate)')
    if not isinstance(op.get('eid'), int) or isinstance(op.get('eid'), bool): raise EditError('eid (element id) must be an integer')
    _ok = _OP_KEYS.get(op['op'])
    if _ok is not None and set(op) - _ok: raise EditError('unknown key(s) %s for %s (a misspelt guard such as match would be silently dropped): nothing was changed' % (sorted(set(op) - _ok), op['op']))
    if not 0 <= op['eid'] < 2 ** 63: raise EditError('eid (element id) is out of range')
    if op['op'] == 'move':
        if BACKEND() != 'rvtedit': raise EditError('move needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        d = [op.get(k, 0.0) for k in ('dx', 'dy', 'dz')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e4 for v in d): raise EditError('dx, dy, dz must be finite numbers (Revit internal units = feet), |v| <= 10000 (VM probe: a +45000 ft move made Revit 2024 raise a far-from-origin dialog on open)')
        if not any(d): raise EditError('move by zero')
        if max(abs(v) for v in d) < 1e-6: raise EditError('move of %.3g ft is below the 1e-6 ft witness resolution (compose drops moves under 1e-12 ft; the gate tolerance is 1e-6 ft, so a smaller move could not be told from no move): refused rather than reported as moved while the file stays unchanged' % max(abs(v) for v in d))
        return {'op': 'move', 'eid': op['eid'], 'dx': float(d[0]), 'dy': float(d[1]), 'dz': float(d[2])}
    if op['op'] == 'change_type':
        if os.environ.get('RVTBALLET_ENABLE_CHANGETYPE') != '1': raise EditError('change_type is disabled (opt-in: RVTBALLET_ENABLE_CHANGETYPE=1; no Revit evidence for it yet)')
        if BACKEND() != 'rvtedit': raise EditError('change_type needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        t = op.get('type_eid')
        if not isinstance(t, int) or isinstance(t, bool) or not 0 <= t < 2 ** 63: raise EditError('type_eid (the FamilySymbol element id) must be an integer')
        return {'op': 'change_type', 'eid': op['eid'], 'type_eid': t}
    if op['op'] == 'set_type_num':
        if os.environ.get('RVTBALLET_ENABLE_TYPEPARAM') != '1': raise EditError('set_type_num is disabled (opt-in: RVTBALLET_ENABLE_TYPEPARAM=1; no Revit evidence for it yet)')
        if BACKEND() != 'rvtedit': raise EditError('set_type_num needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        v = op.get('value'); nm = op.get('param'); pid = op.get('pid')
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e15: raise EditError('value must be a finite number (Revit internal units, feet for lengths)')
        if abs(v) > 1e6 or (v != 0 and abs(v) < 1e-12): raise EditError('value %r is outside the range the writer accepts for a type parameter (|v| <= 1e6, no subnormals); Revit behaviour for such values is unverified' % (v,))
        if v < 0: raise EditError('negative type parameter value %r refused: the Revit VM accepted -5 on a width without an error but its stored result was not verified (it may clamp or reject); nothing was changed' % (v,))
        if (nm is None) == (pid is None): raise EditError('give exactly one of param (the type parameter caption) or pid (its parameter element id)')
        if pid is not None and (not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0): raise EditError('pid must be a positive integer (family parameter element id)')
        if nm is not None and (not isinstance(nm, str) or not nm): raise EditError('param must be a caption string')
        return {'op': 'set_type_num', 'eid': op['eid'], 'pid': pid, 'param': nm, 'value': float(v)}
    if op['op'] == 'set_room_bounding':
        if os.environ.get('RVTBALLET_ENABLE_ROOMBOUND') != '1': raise EditError('set_room_bounding is disabled (opt-in: RVTBALLET_ENABLE_ROOMBOUND=1; no Revit open verdict yet)')
        if BACKEND() != 'rvtedit': raise EditError('set_room_bounding needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        if not isinstance(op.get('value'), bool): raise EditError('value must be true or false')
        return {'op': 'set_room_bounding', 'eid': op['eid'], 'value': op['value']}
    if op['op'] == 'set_type_eid':
        if os.environ.get('RVTBALLET_ENABLE_TYPEEID') != '1': raise EditError('set_type_eid is disabled (opt-in: RVTBALLET_ENABLE_TYPEEID=1; no Revit evidence for it yet)')
        if BACKEND() != 'rvtedit': raise EditError('set_type_eid needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        pid, tgt = op.get('pid'), op.get('target')
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0: raise EditError('pid must be a positive integer (family parameter element id)')
        if not isinstance(tgt, int) or isinstance(tgt, bool) or tgt <= 0: raise EditError('target must be a positive element id')
        return {'op': 'set_type_eid', 'eid': op['eid'], 'pid': pid, 'target': tgt}
    if op['op'] == 'set_type_yesno':
        if os.environ.get('RVTBALLET_ENABLE_TYPEYESNO') != '1': raise EditError('set_type_yesno is disabled (opt-in: RVTBALLET_ENABLE_TYPEYESNO=1; Revit-verified only for one parameter on one 2024 file)')
        if BACKEND() != 'rvtedit': raise EditError('set_type_yesno needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        if op.get('pid') != -1019013 or isinstance(op.get('pid'), bool): raise EditError('only the built-in parameter Export Type to IFC (pid -1019013) is Revit-witnessed for Yes/No create')
        v = op.get('value')
        if isinstance(v, bool): v = int(v)
        if isinstance(v, float) or v not in (0, 1): raise EditError('value must be true/false or 0/1')
        return {'op': 'set_type_yesno', 'eid': op['eid'], 'pid': -1019013, 'value': v}
    if op['op'] == 'set_type_material':
        if os.environ.get('RVTBALLET_ENABLE_TYPEEID') != '1': raise EditError('set_type_material is disabled (opt-in: RVTBALLET_ENABLE_TYPEEID=1; no Revit open verdict yet)')
        if BACKEND() != 'rvtedit': raise EditError('set_type_material needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        tgt = op.get('target')
        if not isinstance(tgt, int) or isinstance(tgt, bool) or tgt <= 0: raise EditError('target must be a positive material element id')
        return {'op': 'set_type_material', 'eid': op['eid'], 'target': tgt}
    if op['op'] == 'rotate':
        if BACKEND() != 'rvtedit': raise EditError('rotate needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        d = op.get('deg')
        if isinstance(d, bool) or not isinstance(d, (int, float)) or d != d or abs(d) > 360: raise EditError('deg must be a finite number of degrees, |deg| <= 360')
        if d % 360 == 0: raise EditError('rotate by a multiple of 360 degrees changes nothing')
        if min(d % 360, 360 - d % 360) < 1e-6: raise EditError('rotate by %.3g degrees (mod 360) is below the 1e-6 degree resolution: smaller angles can leave the stored transform unchanged (accepted as a silent no-op) or be undetectable by the readback witness' % d)
        return {'op': 'rotate', 'eid': op['eid'], 'deg': float(d)}
    if op['op'] == 'set_link_override':
        if os.environ.get('RVTBALLET_ENABLE_LINKOVERRIDE') != '1': raise EditError('link override edit is disabled (opt-in: RVTBALLET_ENABLE_LINKOVERRIDE=1; Revit-verified on 2024 only)')
        if BACKEND() != 'rvtedit': raise EditError('link override edit needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        for k in ('link', 'linked_view'):
            if not isinstance(op.get(k), int) or isinstance(op.get(k), bool) or op[k] <= 0: raise EditError('%s must be a positive element id' % k)
        return {'op': 'set_link_override', 'eid': op['eid'], 'link': op['link'], 'linked_view': op['linked_view']}
    if op['op'] == 'set_link_load':
        if os.environ.get('RVTBALLET_ENABLE_LINKLOAD') != '1': raise EditError('link load-state edit is disabled (opt-in: RVTBALLET_ENABLE_LINKLOAD=1; Revit-verified on 2024 and 2026 only)')
        if BACKEND() != 'rvtedit': raise EditError('link load-state edit needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        if not isinstance(op.get('value'), bool): raise EditError('value must be true (load) or false (unload)')
        return {'op': 'set_link_load', 'eid': op['eid'], 'value': op['value']}
    if op['op'] == 'set_link_path':
        if os.environ.get('RVTBALLET_ENABLE_LINKPATH') != '1': raise EditError('link path edit is disabled (opt-in: RVTBALLET_ENABLE_LINKPATH=1; Revit-verified on 2024 only)')
        if BACKEND() != 'rvtedit': raise EditError('link path edit needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        v = op.get('value')
        if not isinstance(v, str) or not v.strip() or len(v) > 32000 or any(ord(c) < 32 for c in v): raise EditError('link path must be a non-empty string without control characters, at most 32000 chars')
        _check_text(v)
        import unicodedata      # c1x-rvtlink: characters no Windows path can hold, and invisible/format characters (bidi override, zero-width, BOM, noncharacters): refuse instead of storing a path Revit may not round-trip
        if any(c in '<>"|?*' or ord(c) in range(127, 160) or unicodedata.category(c) in ('Cf', 'Cn', 'Co') for c in v) or v != v.rstrip(' .'): raise EditError('link path holds a character Windows paths cannot contain (<>"|?*), an invisible/format/control character, or ends in a space or dot')
        return {'op': 'set_link_path', 'eid': op['eid'], 'value': v}
    if op['op'] == 'delete':
        if os.environ.get('RVTBALLET_ENABLE_DELETE') != '1': raise EditError('delete is disabled (opt-in: RVTBALLET_ENABLE_DELETE=1; no Revit evidence for it yet)')
        if BACKEND() != 'rvtedit': raise EditError('delete needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        return {'op': 'delete', 'eid': op['eid']}
    if op['op'] == 'set_num':
        kind = op.get('kind', 'Double')
        if kind not in ('Double', 'Int'): raise EditError('kind must be Double or Int')
        v = op.get('value')
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e15: raise EditError('value must be a finite number')
        if kind == 'Int' and (not isinstance(v, int) or abs(v) >= 2 ** 31): raise EditError('Int value must be a 32-bit integer')
        if op.get('param') in DERIVED_NUM: raise EditError('parameter %r is a structural-asset value that this reader shows as a derived or placeholder value (not the stored field), so an edit cannot be verified; nothing was changed. Edit it in Revit.' % op.get('param'))
        if kind == 'Int' and op.get('param') in ENUM_INT_RANGE and not ENUM_INT_RANGE[op['param']][0] <= v <= ENUM_INT_RANGE[op['param']][1]: raise EditError('%s %d is not a valid choice (Revit would show it with a blank name); valid values are %d to %d. Nothing was changed.' % (op['param'], v, ENUM_INT_RANGE[op['param']][0], ENUM_INT_RANGE[op['param']][1]))
        if kind == 'Int' and op.get('param') == 'Discipline' and not _discipline_ok(v): raise EditError('Discipline %d is not a valid choice (Revit would show it with a blank name); valid values are 1, 2, 4, 8, 16 and 4095. Nothing was changed.' % v)
        if kind == 'Int' and op.get('param') in READBACK_NEVER_MATCHES_INT: raise EditError('parameter %r: the value shown for it comes from the material asset, not from the stored integer, so an edit cannot be verified; nothing was changed. Edit it in Revit.' % op['param'])
        if kind == 'Int' and op.get('eid') == 0 and op.get('param') in ('Italic', 'Bold', 'Underline'): raise EditError('parameter %r on element 0 (the document-level style holder): the stored integer can be changed, but Revit 2024 (VM readback of racbasicsamplefamily) still shows the old value, so the edit would be accepted yet have no effect; nothing was changed' % op.get('param'))      # c5x-fam2020 item 28
        if op.get('param') in REVIT_IGNORES_STORED_INT: raise EditError('parameter %r: the stored integer can be changed, but the real Revit (2024 and 2026 VM readback) still shows the old value for it, so the edit would have no effect there; nothing was changed. Edit it in Revit.' % op.get('param'))
        pid, cands = _param_spec(op)
        if BACKEND() != 'rvtedit': raise EditError('set_num needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        return {'op': 'set_num', 'eid': op['eid'], 'pid': pid, 'pids': cands, 'param': op.get('param'), 'value': float(v) if kind == 'Double' else int(v), 'kind': kind}
    if not isinstance(op.get('value'), str): raise EditError('value must be a string')
    if op.get('param') is not None or op.get('pid') is not None:       # address the parameter by NAME/ID instead of by old text (several string parameters can hold the same text)
        if BACKEND() != 'rvtedit': raise EditError('editing a parameter by name or id needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        pid, cands = _param_spec(op)
        _check_text(op['value'])
        return {'op': 'set_string', 'eid': op['eid'], 'field': 'ParamValueAString.m_value', 'value': op['value'], 'match': None, 'pid': pid, 'pids': cands, 'param': op.get('param'), 'kind': 'AString', 'expect': op.get('match')}
    _check_text(op['value'])
    f = op.get('field') or DEFAULT_FIELD
    if f not in FIELDS: raise EditError('field %r is not writable (writable: %s)' % (f, ', '.join(FIELDS)))
    m = op.get('match')
    if m is not None and not isinstance(m, str): raise EditError('match must be a string')
    return {'op': 'set_string', 'eid': op['eid'], 'field': f, 'value': op['value'], 'match': m}


class Edits:
    def __init__(self): self.ops = []
    def add(self, op): self.ops.append(validate_op(op)); return len(self.ops)
    def undo(self):
        if not self.ops: raise EditError('nothing to undo')
        return self.ops.pop()
    def manifest(self, deleted=None):
        gone = {'el:%d' % i for i in (deleted or [])}
        m = {'modified': sorted({'el:%d' % o['eid'] for o in compose(self.ops) if o['op'] != 'delete'} - gone)}
        if gone: m['deleted'] = sorted(gone)
        asked = {'el:%d' % o['eid'] for o in compose(self.ops) if o['op'] == 'delete'}
        if asked: m['must_delete'] = sorted(asked)      # savegate: the elements the caller explicitly asked to delete must really be gone from the output (a delete that silently did nothing is refused)
        return m


def compose(ops):
    """the ops of one save with repeated edits of the same thing merged (QUEUE 83: the record editor diffs every op against the ORIGINAL record, so two string edits of one parameter overlapped and corrupted the
    record, and move +2 then move -2 overlaid to -2 instead of 0). Rules: by-name/id parameter edits: the last one per (element, parameter, kind) wins; moves of one element add up; rotations of one element add up
    (a rotation about the instance's own origin commutes with a translation); a net zero move / rotation is dropped (the element is unchanged, so it is not declared either); every other op on a deleted element is dropped.
    Ops without a parameter name/id (text-match edits) are kept as they are, in order."""
    import math
    dels = {o['eid'] for o in ops if o['op'] == 'delete'}; seen_del = set(); out = []; slot = {}
    for o in ops:
        e = o['eid']; k = None
        if o['op'] == 'delete':
            if e in seen_del: continue
            seen_del.add(e); out.append(o); continue
        if e in dels: continue
        if o['op'] in ('set_string', 'set_num') and (o.get('param') is not None or o.get('pid') is not None): k = (o['op'], e, o.get('kind'), o.get('pid'), o.get('param'))
        elif o['op'] == 'move': k = ('move', e)
        elif o['op'] == 'rotate': k = ('rotate', e)
        elif o['op'] == 'set_type_num': k = ('set_type_num', e, o.get('pid'), o.get('param'))
        elif o['op'] == 'set_type_eid': k = ('set_type_eid', e, o.get('pid'))
        elif o['op'] == 'set_type_yesno': k = ('set_type_yesno', e, o.get('pid'))
        elif o['op'] == 'set_room_bounding': k = ('set_room_bounding', e)      # the last value wins
        elif o['op'] == 'set_type_material': k = ('set_type_material', e)
        elif o['op'] == 'change_type': k = ('change_type', e)      # the last type wins
        elif o['op'] == 'set_link_load': k = ('set_link_load', e)      # the last value wins
        elif o['op'] == 'set_link_path': k = ('set_link_path', e)      # the last path wins
        elif o['op'] == 'set_link_override': k = ('set_link_override', e, o['link'])      # the last setting wins
        if k is None: out.append(o); continue
        if k in slot:
            i = slot[k]
            if o['op'] == 'move': out[i] = dict(out[i], dx=out[i]['dx'] + o['dx'], dy=out[i]['dy'] + o['dy'], dz=out[i]['dz'] + o['dz'])
            elif o['op'] == 'rotate': out[i] = dict(out[i], deg=out[i]['deg'] + o['deg'])
            else: out[i] = o
        else: slot[k] = len(out); out.append(dict(o))
    keep = []
    for o in out:
        if o['op'] == 'move' and max(abs(o['dx']), abs(o['dy']), abs(o['dz'])) > 1e4: raise EditError('the moves of element %d add up beyond 10000 ft; nothing was changed' % o['eid'])
        if o['op'] == 'move' and max(abs(o['dx']), abs(o['dy']), abs(o['dz'])) < 1e-12: continue
        if o['op'] == 'rotate' and abs(math.remainder(o['deg'], 360.0)) < 1e-9: continue
        keep.append(o)
    return keep


def apply(buf, ops): return apply_full(buf, ops)[0]


_DIRTY = __import__('threading').local()      # per thread: {partition stream: set(member idx)} the writer rewrote during the last apply_full (None = could not be determined)


def last_dirty_members():
    d = getattr(_DIRTY, 'd', None)
    return None if d is None else {k: sorted(v) for k, v in d.items()}


def member_diff_ranges(src, out, dm):
    """{stream: {str(member): [[lo, hi), ...]}} the exact byte runs the writer changed inside each declared dirty member (equal-length members only; a length change gets no entry). The gate (manifest member_diff_ranges) then refuses any byte that differs outside them: a flip next to the edit, inside the span window but outside the writer's own runs, was ACCEPTED (c2x-rvtsave 2026-11-12)."""
    import cfb, rvtw, wlpart
    a, b = cfb.CFB(src).streams(), cfb.CFB(out).streams(); res = {}
    for pn, mem in (dm or {}).items():
        pa, pb = wlpart.Partition(rvtw.Stream(a[pn].data)), wlpart.Partition(rvtw.Stream(b[pn].data))
        for mi in mem:
            ra, rb = bytes(pa.mem[mi]['raw']), bytes(pb.mem[mi]['raw'])
            if len(ra) != len(rb): continue
            runs = []; i = 0; n = len(ra)
            while i < n:
                if ra[i] != rb[i]:
                    j = i
                    while j < n and ra[j] != rb[j]: j += 1
                    runs.append([i, j]); i = j
                else: i += 1
            res.setdefault(pn, {})[str(mi)] = runs
    return res


def member_raw_digests(out, dm):
    """{stream: {str(member): sha256 hex of the decompressed member}} of the writer's own output, for every declared dirty member. The gate (manifest member_raw_sha256) requires the output member to equal it exactly: member_diff_ranges only bounds WHERE bytes differ, a flip of a byte the writer itself changed (rotate: 2 of 6 window flips, c2x-rvtsave 2026-11-12) passed it."""
    import cfb, rvtw, wlpart, hashlib
    b = cfb.CFB(out).streams(); res = {}
    for pn, mem in (dm or {}).items():
        pb = wlpart.Partition(rvtw.Stream(b[pn].data))
        for mi in mem: res.setdefault(pn, {})[str(mi)] = hashlib.sha256(bytes(pb.mem[mi]['raw'])).hexdigest()
    return res


def _sweep_stale_edit_dirs(max_age=6 * 3600):
    """a SIGKILL/power loss in the middle of an edit leaves rvtballet-edit-* (a full copy of the user's model) in the temp dir; remove our own such dirs older than max_age (an edit takes minutes)"""
    import time, shutil
    td = tempfile.gettempdir(); now = time.time()
    try: names = os.listdir(td)
    except OSError: return 0
    n = 0
    for nm in names:
        if not nm.startswith('rvtballet-edit-'): continue
        p = os.path.join(td, nm)
        try:
            st = os.lstat(p)
            if os.path.isdir(p) and not os.path.islink(p) and st.st_uid == os.getuid() and now - st.st_mtime > max_age: shutil.rmtree(p, ignore_errors=True); n += 1
        except OSError: pass
    return n


ASM_MOVED = []      # (member eid, dx, dy, dz) of every nested-assembly member the lab writer moved besides the op's own element (c4x-rvtdiff 144): the save path declares them as moves so the gate checks each one


def apply_full(buf, ops):
    """replay ops on bytes -> new bytes (the source bytes are never modified). Backend: env RVTBALLET_EDIT_BACKEND = wledit (default) | rvtedit"""
    ops = compose(ops); _DIRTY.d = {}; ASM_MOVED[:] = []
    if not ops: return buf, []
    _sweep_stale_edit_dirs()
    d = tempfile.mkdtemp(prefix='rvtballet-edit-'); a = os.path.join(d, 'in.rvt'); b = os.path.join(d, 'out.rvt')
    try:
        with open(a, 'wb') as f: f.write(buf)
        deleted = (_apply_rvtedit if BACKEND() == 'rvtedit' else _apply_wledit)(a, b, ops) or []
        with open(b, 'rb') as f: out = f.read()
        _check_member_limit(buf, out)
        _check_first_member(buf, out)
        return out, deleted
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)      # everything in it, including intermediate pass files of a failed multi-partition run


def _max_member_raw(buf):
    """largest raw (decompressed) size of any partition member in the file; 0 when there is none"""
    if WL not in sys.path: sys.path.insert(0, WL)
    import cfb, rvtw, wlpart
    big = 0
    for n, e in cfb.CFB(buf).streams().items():
        if n.startswith('Partitions/'):
            big = max([big] + [len(m['raw']) for m in wlpart.Partition(rvtw.Stream(e.data)).mem])
    return big


def _first_members(buf):
    """{partition stream name: raw size of its first member}"""
    if WL not in sys.path: sys.path.insert(0, WL)
    import cfb, rvtw, wlpart
    r = {}
    for n, e in cfb.CFB(buf).streams().items():
        if n.startswith('Partitions/'):
            m = wlpart.Partition(rvtw.Stream(e.data)).mem
            if m: r[n] = len(m[0]['raw'])
    return r


def _check_first_member(src, out):
    """c3x-rvtdiff 2026-11-15 (Revit 2024 VM verdict: iso_t3/iso_rot/iso_t3_mv = CorruptModelException 105): a full first partition member (>100000 B) that shrinks to a tiny one (<1000 B) is the layout Revit refuses"""
    b = _first_members(out)
    if not any(v < 1000 for v in b.values()): return      # common case: one scan of the output only
    a = _first_members(src)
    for n, v in a.items():
        if v > 100000 and b.get(n, v) < 1000:
            raise EditError('edit refused: first partition member of %s would shrink from %d to %d bytes; Revit rejects this layout, nothing written' % (n, v, b[n]))


def _check_member_limit(src, out):
    """c5x-rvttype 2026-11-13: a partition member above 131088 raw bytes (or above the largest one the source already had) is rejected by Revit (CorruptModelException) although our reader accepts it: never return such an output"""
    got = _max_member_raw(out)
    if got <= 131088: return      # the common case costs one scan of the output only
    lim = max(131088, _max_member_raw(src))
    if got > lim: raise EditError('edit refused: the result would contain a partition member of %d bytes (limit %d); Revit rejects such a file, nothing written' % (got, lim))


def _apply_wledit(a, b, ops):
    if WL not in sys.path: sys.path.insert(0, WL)
    import wledit
    ed = wledit.Editor(a)
    for o in ops:
        if o['op'] != 'set_string': raise EditError('op %s needs the rvtedit backend' % o['op'])
        try: ed.set_string(o['eid'], o['field'], o['value'], match=o['match'])
        except (IndexError, KeyError, StopIteration, AssertionError, struct_error()) as e:
            raise EditError('element %d has no %s to edit (%s)' % (o['eid'], o.get('field') or ('parameter %s' % o.get('pid')), type(e).__name__))
    ed.save(b)


def _eid_val(t):
    """signed id from a trace 'EID(n)' text: 8-byte ids are unsigned 64-bit, the 4-byte layout (Revit 2019-2023 nested) prints unsigned 32-bit; negative parameter ids must compare equal across both"""
    try: v = int(str(t)[4:-1])
    except ValueError: return None
    return v - (1 << 64) if v >= (1 << 63) else v - (1 << 32) if (1 << 31) <= v < (1 << 32) else v


def _resolve_pid(ed, o):
    """explicit pid, or the single candidate id for the parameter NAME that is actually stored (as the given kind) on this element"""
    if o.get('pid') is not None: return o['pid']
    log = ed.g.e.trace(o['eid'])[3]; stored = set()
    for l in log:
        if l[1] == 'ParamValue%s.m_paramId' % o['kind']:
            v = _eid_val(l[4])
            if v is not None: stored.add(v)
    hit = [c for c in o['pids'] if c in stored]
    if len(hit) != 1: raise EditError('parameter %r: %d candidate ids stored as %s on element %d (need exactly 1; give pid)' % (o.get('param'), len(hit), o['kind'], o['eid']))
    return hit[0]


def _apply_rvtedit(a, b, ops):
    """rvtedit works on ONE partition per save (env PART): in multi-partition files the ops are grouped by the partition each element lives in and applied as sequential passes (pass n reads the output of pass n-1), as rvtedit's own
    command line does. Order WITHIN a partition is the recorded order; across partitions it follows the grouping, so a delete is not allowed to share a save with edits in other partitions (its cascade could touch them)."""
    for p in (EL, WL, os.path.expanduser('~/rvt-research')):
        if p not in sys.path: sys.path.insert(0, p)
    os.environ.setdefault('RVT_GEOM', '1')
    try: import rvtedit, cfb
    except ImportError as e: raise EditError('the rvtedit backend is not available (%s); install/point RVTBALLET_EDITLAB and RVTBALLET_WRITELAB' % e)
    _lk = [(o['op'], o.get('eid')) for o in ops if o.get('op') in ('set_link_path', 'set_link_load')]
    if len(_lk) != len(set(_lk)): raise EditError('two link path (or load) ops on one link type reached the editor un-coalesced: the second works from record offsets the first shifted and flipped the load flag (c1x-rvtlink item 95c, 2024 VM-less readback); refused')
    saved_part = os.environ.get('PART'); tmps = []
    try:
        os.environ.pop('PART', None); groups = {}
        try:
            with open(a, 'rb') as f: n_parts = sum(1 for k in cfb.CFB(f.read()).streams() if k.startswith('Partitions/'))      # cheap: no model decode for single-partition files
        except Exception: n_parts = 1      # not parseable here: let the editor report the real problem
        if n_parts > 1:
            probe = rvtedit.Edit(a)
            for o in ops:
                try:
                    pn = (getattr(probe, 'latest_partition', lambda e: None)(o['eid']) or probe.g.e.trace(o['eid'])[0])
                    if o['op'] not in ('set_link_path', 'set_link_load') and not (o['op'] in ('set_string', 'set_num') and o.get('kind') in ('AString', 'Double', 'Int') and os.environ.get('RVTBALLET_MULTIPART_PARAM') == '1') and isinstance(o.get('eid'), int) and len({q for q, *_ in probe.g.e.m.find(o['eid'])}) > 1 and os.environ.get('RVTBALLET_MULTIPART_OK') != '1':      # c5x-rvtlink 2026-11-13: the episode heuristic picked the copy Revit ignores for a 2026 link type (silent no-op the witness cannot see)
                        raise EditError('element %d has records in several partitions (Revit may read a copy this edit would not change; 2026 Electrical sample: 19%% of sampled elements, 2024 Facades: 0%%): %s refused' % (o['eid'], o['op']))
                    if o['op'] == 'rotate' and pn != probe.g.e.trace(o['eid'])[0]:      # older copy elsewhere: the reader sees the OLD copy, so the rotation could not be verified (QUEUE 59e)
                        raise EditError('element %d has records in several partitions (the edit would go to the newest copy, which the viewer cannot read back): rotate refused' % o['eid'])
                except EditError: raise
                except Exception: pn = None
                if o['op'] in ('set_link_path', 'set_link_load') or (o['op'] in ('set_string', 'set_num') and o.get('kind') in ('AString', 'Double', 'Int') and os.environ.get('RVTBALLET_MULTIPART_PARAM') == '1'):      # c5x-rvtlink: edit EVERY partition copy of the link type (2026 Electrical: 39 and 41, Revit reads 41); one pass per partition
                    try: _ps = sorted({str(q) for q, *_ in probe.g.e.m.find(o['eid'])})
                    except Exception: _ps = []
                    if len(_ps) > 1:
                        for q in _ps: groups.setdefault(q, []).append(o)
                        continue
                groups.setdefault(pn, []).append(o)
            del probe
            if len(groups) > 1 and any(o['op'] == 'delete' for o in ops): raise EditError('a delete cannot be saved together with edits in other partitions of this file (the order across partitions is not preserved): save the delete separately')
        else: groups[None] = list(ops)
        deleted = []; cur = a
        passes = []      # (partition, ops): the editor computes a move/rotate from the ORIGINAL record and refuses a second one on the same element in a session, so a move and a rotate of one element go to consecutive passes (pass 2 reads the output of pass 1, like two saves in a row)
        for pn, grp in groups.items():
            chunk, hit = [], set()
            for o in grp:
                if o['op'] in ('move', 'rotate'):
                    if o['eid'] in hit: passes.append((pn, chunk)); chunk, hit = [], set()
                    hit.add(o['eid'])
                chunk.append(o)
            passes.append((pn, chunk))
        for n, (pn, grp) in enumerate(passes):
            last = n == len(passes) - 1; out = b if last else os.path.join(os.path.dirname(b), 'pass%d.rvt' % n)
            if pn: os.environ['PART'] = str(pn)
            else: os.environ.pop('PART', None)
            if not last: tmps.append(out)
            deleted += _rvtedit_pass(cur, out, grp)
            cur = out
        return deleted
    finally:
        for t in tmps:
            try: os.remove(t)
            except OSError: pass
        if saved_part is None: os.environ.pop('PART', None)
        else: os.environ['PART'] = saved_part


def _body(ed, eid):
    """buffer that the trace offsets of element eid index: the element's own partition body (ed.g.bj is another buffer on some files, e.g. 2020 Hyperloop: reads there were garbage, c7x-rvtmove item 25)"""
    try: return ed.g.e.m.parts[ed.g.e.trace(eid)[0]]['joined']
    except Exception: return ed.g.bj


def _trf_or(ed, eid):
    """first Trf.m_or triple of the element record (own partition), or None"""
    import struct
    try:
        l = [x for x in ed.g.e.trace(eid)[3] if x[1] == 'Trf.m_or']
        return struct.unpack_from('<3d', _body(ed, eid), l[0][2]) if l else None
    except Exception: return None


def _is_pinned(ed, eid):
    """Element.m_locked (Revit Pinned): Revit-made witness, Grid 1363058 HVAC 2024 pinned by the API flips exactly Element.m_locked 0 -> 1. Revit's own API refuses to move a pinned element, so we refuse too."""
    try:
        for l in ed.g.e.trace(eid)[3]:
            if l[1].startswith('Element.m_locked') and l[3] - l[2] == 1: return _body(ed, eid)[l[2]] != 0
    except Exception: return False
    return False


def _field64(ed, eid, name):
    import struct
    for l in ed.g.e.trace(eid)[3]:
        if l[1] == name and l[3] - l[2] == 8: return struct.unpack_from('<Q', _body(ed, eid), l[2])[0]
    return None


def _set_link_path(ed, o):
    """RvtLinkSymbol path: rewrite ModelPath.m_path, the std::pair<AString,AString>.second copy and the old path inside ExternalResourceRef.m_displayPath (Revit 2024 VM: same length and +14 chars open clean, readback = new path). Refused unless the record has ModelPath.m_path."""
    import struct
    from rvtedit import _u16
    if os.environ.get('RVTBALLET_LINKPATH_ANY_YEAR') != '1':      # Revit-verified on 2024 only (VM); other years: layout not confirmed
        import re as _re, cfb as _cfb
        try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(ed.src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
        except Exception: raise EditError('link path edit refused: cannot read the Revit version of the file')
        if fy not in (2024, 2025, 2026): raise EditError('link path edit is only verified on Revit 2024/2025/2026 files (this file is %d): refused' % fy)
    try: log = ed.g.e.trace(o['eid'])[3]
    except (IndexError, KeyError, StopIteration, OverflowError, TypeError, ValueError): raise EditError('element %r does not exist in this file: link path edit refused' % (o['eid'],))
    olds = [l for l in log if l[1] == 'ModelPath.m_path']
    if not olds: raise EditError('element %d is not a link type (no ModelPath.m_path): link path edit refused' % o['eid'])
    try: _parts = {pn for pn, *_ in ed.g.e.m.find(o['eid'])}
    except Exception: _parts = set()
    if len(_parts) > 1 and not os.environ.get('PART'): raise EditError('element %d has records in several partitions (%s): Revit may read a copy this edit does not change (Revit 2026 VM 2026-11-13, silent no-op): link path edit refused' % (o['eid'], ', '.join(sorted(map(str, _parts)))))
    def full(l):
        b = _body(ed, o['eid']); n = struct.unpack_from('<I', b, l[2])[0]; return bytes(b[l[2] + 4:l[2] + 4 + 2 * n]).decode('utf-16le')      # the element's own partition body (ed.g.bj is another buffer on 2025 files: reads were garbage)
    try: old = full(olds[0])      # the reader's l[4] is display-truncated (60 chars): using it duplicated the tail of long paths inside the display path
    except (UnicodeDecodeError, struct.error): raise EditError('element %d: the link path bytes do not decode as the verified (2024) layout: refused' % o['eid'])
    if not isinstance(old, str) or not old: raise EditError('element %d: existing link path is empty or unreadable: refused' % o['eid'])
    # Revit 2024 VM 2026-11-13 (c5x-rvtlink, 6 odd-path variants): <>|?*, '..' segments, reserved device names and trailing dot/space opened without repair but gave NotFound/normalised/mismatched paths: refuse them
    import re as _re2
    _v = o['value']
    if not isinstance(_v, str) or not _v or _re2.search(r'[<>"|?*\x00-\x1f]', _v): raise EditError('link path has empty value or characters Windows forbids (<>"|?* or control): refused')
    try: _v.encode('utf-16-le')
    except UnicodeEncodeError: raise EditError('link path has an unpaired surrogate (not valid UTF-16): refused')
    if len(_v) > 259: raise EditError('link path is %d chars (> 259, Windows MAX_PATH): refused, Revit behaviour beyond it is untested' % len(_v))
    if ':' in _v and not _re2.fullmatch(r'[A-Za-z]:[\\/][^:]*', _v): raise EditError("link path has a ':' that is not the drive designator (Windows forbids it in names; NTFS stream syntax): refused")
    if _re2.search(r'[\\/]$', _v) or _re2.search(r'(?<!^)[\\/]{2,}', _v): raise EditError('link path ends with a separator or has an empty segment (a directory / a path Windows normalises, the stored path would not match): refused')
    if '/' in _v: raise EditError("link path contains '/': Revit 2024 VM 2026-11-16 (rb93) drops the directory of such a path and reads back the bare file name, so it is not a separator there; use backslashes: refused")
    _segs = [x for x in _re2.split(r'[\\/]', _v) if x]
    if any(x in ('.', '..') for x in _segs): raise EditError("link path contains '.' or '..' segments (Revit normalises them, the stored path would not match): refused")
    if any(x != x.rstrip(' .') or _re2.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?', x) for x in _segs): raise EditError('link path has a reserved device name or a segment ending in dot or space: refused')
    # Revit keeps ONE link type per linked file: two link types on one path both fail to load (Revit 2024 VM 2026-11-13, c5x-rvtlink), so refuse a path another link type already has
    try:
        import sys as _sys
        for _pth in ('~/rvt-research', '~/rvt-research/write-lab'):
            if os.path.expanduser(_pth) not in _sys.path: _sys.path.insert(0, os.path.expanduser(_pth))
        from . import save as _sv; _P = _sv._read_params(open(ed.src, 'rb').read())
        _others = [e for e, d in _P.items() if e != o['eid'] and isinstance(d, dict) and d.get('class') == 'RvtLinkSymbol']
    except Exception: raise EditError('link path edit refused: cannot list the other link types to check for a duplicate path')
    import unicodedata as _ud
    _nrm = lambda t: _ud.normalize('NFC', t.replace('/', '\\')).casefold()      # NFC/NFD and case variants of one name are one file on Windows
    _nv = _nrm(o['value'])
    for _e in _others:
        for _l in ed.g.e.trace(_e)[3]:
            if _l[1] == 'ModelPath.m_path':
                _n = struct.unpack_from('<I', _body(ed, _e), _l[2])[0]; _op = bytes(_body(ed, _e)[_l[2] + 4:_l[2] + 4 + 2 * _n]).decode('utf-16le', 'replace')
                if _nrm(_op) == _nv: raise EditError('link type %d already points at %r: Revit keeps one link type per file (two on one path both fail to load); nothing was changed' % (_e, _op))
                break
    if o['value'] == old: raise EditError('link type %d already has this path: nothing to change (a same-value edit rewrote and re-compressed the whole partition; refused, file untouched)' % o['eid'])
    edits = []
    for l in log:
        if l[1] in ('ModelPath.m_path', 'std::pair< AString, AString >.second') and full(l) == old: edits.append((l[2], l[3] - l[2], _u16(o['value'])))
        if l[1] == 'ExternalResourceRef.m_displayPath':
            d = full(l)
            if d.endswith(old): nd = d[:-len(old)] + o['value']      # the stored path is the display path's tail; replace only that, never an equal substring in a folder name
            elif d.count(old) == 1: nd = d.replace(old, o['value'])
            else: raise EditError('element %d: old link path occurs %d times in the display path and not at its end: refused' % (o['eid'], d.count(old)))
            edits.append((l[2], l[3] - l[2], _u16(nd)))
    if len(edits) < 2: raise EditError('element %d: unexpected link record layout (%d path spans): refused' % (o['eid'], len(edits)))
    ed._rec_edit(o['eid'], edits)


# one RvtLinkDisplaySettings map (count 1 + one std::pair<ElementId,RvtLinkDisplaySettings> entry), 142 bytes, copied from the Revit 2024 VM result of View.SetLinkOverrides(linkTypeId, ByLinkView + LinkedViewId) on the Autodesk HVAC sample (view record 1363877): key at [4:12], RvtLinkDisplaySettings.m_linkedView at [20:28]
_LINK_OVR_TEMPLATE = bytes.fromhex('01000000e1cf14000000000000000000000000001ae501000000000000000000ffffffffffffffffffffffffffffffff00000000010000000100000000000000010000000100000000000000010000000100000001000000010000000100000001000000010000000100000001000000000000000100000001000000010000000100000001000000000000000000')


def _set_link_load(ed, o):
    """RvtLinkSymbol.m_shouldLoadSource 1 byte (Revit VM: 2024 HVAC and 2026 Structural, unload = IsLoaded True->False, other links unchanged; the TransmissionData DesiredLoadState copy is not needed). 2025 and older years are not VM-verified: refused. Link types with records in several partitions are refused."""
    import struct
    import re as _re, cfb as _cfb
    try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(ed.src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
    except Exception: raise EditError('link load-state edit refused: cannot read the Revit version of the file')
    if fy not in (2024, 2026): raise EditError('link load-state edit is only verified on Revit 2024/2026 files (this file is %d): refused' % fy)
    try: log = ed.g.e.trace(o['eid'])[3]
    except (IndexError, KeyError, StopIteration, OverflowError, TypeError, ValueError): raise EditError('element %r does not exist in this file: link load-state edit refused' % (o['eid'],))
    ls = [l for l in log if l[1] == 'RvtLinkSymbol.m_shouldLoadSource']
    if len(ls) != 1 or ls[0][3] - ls[0][2] != 1: raise EditError('element %d is not a link type with a one-byte load flag: refused' % o['eid'])
    try: _parts = {pn for pn, *_ in ed.g.e.m.find(o['eid'])}
    except Exception: _parts = set()
    if len(_parts) > 1 and not os.environ.get('PART'): raise EditError('element %d has records in several partitions: Revit may read a copy this edit does not change: link load-state edit refused' % o['eid'])
    b = _body(ed, o['eid'])
    if b[ls[0][2]] not in (0, 1): raise EditError('element %d: unexpected load flag value %d: refused' % (o['eid'], b[ls[0][2]]))
    if b[ls[0][2]] == (1 if o['value'] else 0): raise EditError('link type %d is already %s: nothing to change (a no-op edit used to rewrite and re-compress the whole partition; refused, file untouched)' % (o['eid'], 'loaded' if o['value'] else 'unloaded'))
    ed._rec_edit(o['eid'], [(ls[0][2], 1, bytes([1 if o['value'] else 0]))])


def _set_link_override(ed, o):
    """View link override 'by linked view': inserts one entry into RvtLinkOverrides.m_displaySettingsMap of a view record (Revit 2024 VM: the only change Revit made to the file is this 142-byte replacement of the map count in the view record). v1 handles the EMPTY map only (refuses a view that already has overrides) and needs the view to have RvtLinkOverrides; the link must be a RvtLinkSymbol/type of the file."""
    import struct
    import re as _re, cfb as _cfb
    if os.environ.get('RVTBALLET_LINKOVR_ANY_YEAR') != '1':
        try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(ed.src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
        except Exception: raise EditError('link override edit refused: cannot read the Revit version of the file')
        if fy != 2024: raise EditError('link override edit is only verified on Revit 2024 files (this file is %d): refused' % fy)
    if len(_LINK_OVR_TEMPLATE) != 142: raise EditError('internal: override template size')
    for _k in ('eid', 'link', 'linked_view'):
        if type(o.get(_k)) is not int or not 0 <= o[_k] < 2 ** 62: raise EditError('link override: %s must be a non-negative element id (got %r): refused' % (_k, o.get(_k)))
    if o['link'] not in ed.g.e.m.ids: raise EditError('link element %d does not exist' % o['link'])
    try: _lk = ed.g.e.trace(o['link'])[3]
    except (IndexError, KeyError, StopIteration): raise EditError('link element %d cannot be decoded: link override refused' % o['link'])
    if not any(l[1].startswith('RvtLinkSymbol.') for l in _lk): raise EditError('element %d is not a Revit link type (no RvtLinkSymbol fields): link override refused' % o['link'])
    try: log = ed.g.e.trace(o['eid'])[3]
    except (IndexError, KeyError, StopIteration): raise EditError('element %d does not exist in this file: link override refused' % o['eid'])
    mp = [l for l in log if l[1] == 'RvtLinkOverrides.m_displaySettingsMap']
    if len(mp) != 1: raise EditError('element %d has no RvtLinkOverrides (not a view with link overrides): refused' % o['eid'])
    s, e = mp[0][2], mp[0][3]
    if e - s != 4 or struct.unpack_from('<I', ed.g.bj, s)[0] != 0: raise EditError('element %d already has link display overrides: v1 only fills an empty map; refused' % o['eid'])
    ent = bytearray(_LINK_OVR_TEMPLATE)
    struct.pack_into('<Q', ent, 4, o['link']); struct.pack_into('<Q', ent, 20, o['linked_view'])
    ed._rec_edit(o['eid'], [(s, 4, bytes(ent))])


def _change_type(ed, o):
    """point a FamilyInstance at another FamilySymbol of the SAME family: overwrite FamilyInstance.m_masterSymbolId (8-byte ElementId) in the instance record. Refused unless the instance has that field, the target has FamilySymbol.m_familyId, and both families are equal (a symbol of another family would need a different geometry / host relation)"""
    if os.environ.get('RVTBALLET_CHANGETYPE_ANY_YEAR') != '1':      # Revit-verified on 2024/2026 only (VM); other years were never gated
        import re as _re, cfb as _cfb
        try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(ed.src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
        except Exception: raise EditError('change_type refused: cannot read the Revit version of the file')
        if fy not in (2024, 2026): raise EditError('change_type is only verified on Revit 2024/2026 files (this file is %d): refused' % fy)
    cur = _field64(ed, o['eid'], 'FamilyInstance.m_masterSymbolId')
    if cur is None: raise EditError('element %d is not a family instance (no FamilyInstance.m_masterSymbolId): change_type refused' % o['eid'])
    try: fam_new = _field64(ed, o['type_eid'], 'FamilySymbol.m_familyId')
    except (IndexError, KeyError): raise EditError('element %d does not exist in this file: change_type refused' % o['type_eid'])
    if fam_new is None: raise EditError('element %d is not a family type (no FamilySymbol.m_familyId): change_type refused' % o['type_eid'])
    fam_old = _field64(ed, cur, 'FamilySymbol.m_familyId')
    if fam_old is None or fam_old != fam_new: raise EditError('type %d belongs to another family than the current type %d of element %d: change_type refused (same-family types only)' % (o['type_eid'], cur, o['eid']))
    if cur == o['type_eid']: raise EditError('element %d already has type %d' % (o['eid'], cur))
    mid = _field64(ed, o['type_eid'], 'FamilySymbol.m_masterId')      # surrogate/derived symbol: Revit API ChangeTypeId refused it (2024 HVAC: 1530089, m_masterId=1379030, empty name)
    if mid is not None and mid != 0xFFFFFFFFFFFFFFFF and os.environ.get('RVTBALLET_TEST_ALLOW_DERIVED_TYPE') != '1': raise EditError('type %d is a derived symbol of type %d (FamilySymbol.m_masterId set), not a user type: change_type refused (Revit rejects it)' % (o['type_eid'], mid))
    ed.set_field(o['eid'], 'FamilyInstance.m_masterSymbolId', o['type_eid'], fmt='<Q')


def _set_room_bounding(ed, o):
    """Room Bounding yes/no on a host object (wall/floor/...): one byte HostObj.m_roomBounding (paired Revit experiment, Structural 2024 wall: 01 -> 00, only that byte plus regenerated caches changed). Refused unless the field is exactly 1 byte holding 0 or 1."""
    try: log = ed.g.e.trace(o['eid'])[3]
    except (IndexError, KeyError): raise EditError('element %d does not exist in this file: set_room_bounding refused' % o['eid'])
    f = [l for l in log if l[1] == 'HostObj.m_roomBounding']
    if len(f) != 1 or f[0][3] - f[0][2] != 1: raise EditError('element %d has no single-byte HostObj.m_roomBounding: refused' % o['eid'])
    cur = _body(ed, o['eid'])[f[0][2]]
    if cur not in (0, 1): raise EditError('element %d: m_roomBounding holds %d (not 0/1): refused' % (o['eid'], cur))
    if cur == int(o['value']): raise EditError('element %d: Room Bounding is already %s' % (o['eid'], bool(cur)))
    ed.set_field(o['eid'], 'HostObj.m_roomBounding', int(o['value']), fmt='<B')


def _move_datum(ed, o):
    """Level / Grid move: the datum's position is Plane.m_origin (stored twice in the element record; DatumPlane.m_freeEnd/m_bubbleEnd are constant defaults, measured on Autodesk HVAC 2024).
    Level: only dz (a level is a horizontal plane; in-plane shifts are refused). Grid: only the component along the plane normal (shifting a grid along its own line changes extents that are not rewritten here: refused)."""
    import struct, math
    g = ed.g; log = g.e.trace(o['eid'])[3]
    org = [l for l in log if l[1] == 'Plane.m_origin' and l[3] - l[2] == 24]
    xv = [l for l in log if l[1] == 'Plane.m_xVec' and l[3] - l[2] == 24]; yv = [l for l in log if l[1] == 'Plane.m_yVec' and l[3] - l[2] == 24]
    if len(org) != 2 or len(xv) != 2 or len(yv) != 2: raise NotImplementedError('class datum: unexpected Plane layout (%d origins)' % len(org))
    B = _body(ed, o['eid']); x = struct.unpack_from('<3d', B, xv[0][2]); y = struct.unpack_from('<3d', B, yv[0][2])
    n = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]); L = math.sqrt(sum(c * c for c in n))
    if not 0.999 < L < 1.001: raise NotImplementedError('class datum: plane axes are not orthonormal')
    n = tuple(c / L for c in n); d = (o['dx'], o['dy'], o['dz']); dn = sum(d[i] * n[i] for i in range(3))
    inplane = math.sqrt(max(0.0, sum(c * c for c in d) - dn * dn))
    if inplane > 1e-9: raise EditError('element %d: only a move perpendicular to the %s (along its normal) is supported; the in-plane part (%.6g) was refused' % (o['eid'], 'level plane' if o['cls'] == 'Level' else 'grid plane', inplane))
    sh = tuple(dn * c for c in n); edits = []
    for l in org:
        v = struct.unpack_from('<3d', B, l[2]); edits.append((l[2], 24, struct.pack('<3d', *(v[i] + sh[i] for i in range(3)))))
    ed._rec_edit(o['eid'], edits)


def _move_viewport(ed, o):
    """Viewport (a view placed on a sheet): the placement is Viewport.m_offset (sheet coordinates, ft) and the label origin Viewport.m_labelOrigin moves with it. Measured in the Revit 2024 VM (Snowdon Structural, API SetBoxCenter +0.25,+0.125): exactly these two fields shifted by (dx,dy,0), nothing else of the Viewport/Viewer/sheet records changed. Opt-in (RVTBALLET_ENABLE_VIEWPORTMOVE=1) until our own output is VM-verified."""
    import struct
    if o['dz']: raise EditError('element %d: a viewport moves in the sheet plane only (dz must be 0)' % o['eid'])
    log = ed.g.e.trace(o['eid'])[3]; B = _body(ed, o['eid']); edits = []
    for nm in ('Viewport.m_offset', 'Viewport.m_labelOrigin'):
        f = [l for l in log if l[1] == nm and l[3] - l[2] == 24]
        if len(f) != 1: raise EditError('element %d: unexpected Viewport layout (%d x %s), move refused' % (o['eid'], len(f), nm))
        v = struct.unpack_from('<3d', B, f[0][2]); edits.append((f[0][2], 24, struct.pack('<3d', v[0] + o['dx'], v[1] + o['dy'], v[2])))
    ed._rec_edit(o['eid'], edits)


def _rvtedit_pass(a, b, ops):
    import rvtedit
    ed = rvtedit.Edit(a); deleted = []; ed._deleted_ids = deleted
    _check_batch_names(ops)
    for o in ops:
        try:
            if o['op'] == 'delete':
                if o['eid'] in deleted: continue      # already removed by an earlier delete's cascade: no second removal
                deleted += [i for i in _delete(ed, o['eid']) if i not in deleted]
            elif o['op'] == 'move':
                if _is_pinned(ed, o['eid']): raise EditError('element %d is pinned (Element.m_locked): moving a pinned element is refused, as Revit does; unpin it first' % o['eid'])
                _o0 = _trf_or(ed, o['eid'])
                try:
                    if any(str(x[1]).startswith('StructFootingUserData.') for x in ed.g.e.trace(o['eid'])[3]): raise EditError('element %d: move refused, it is a structural footing (StructFootingUserData / StructAttachInfo): its bounding box does not follow the placement origin (rst_basic 2023 element 512451: box shift 0 for a requested 1 ft move)' % o['eid'])
                    if _o0 == (0.0, 0.0, 0.0) and not any(str(x[1]).startswith('GLine') for x in ed.g.e.trace(o['eid'])[3]): raise EditError('element %d: move refused, its placement origin Trf.m_or is exactly (0,0,0) (host-relative or unplaced), so a move would not change the record; nothing was changed' % o['eid'])
                    if any(str(x[1]).startswith('FamInstCurveDriver.') for x in ed.g.e.trace(o['eid'])[3]): raise EditError('element %d: move refused, it is a curve-located family instance (beam / brace: FamInstCurveDriver with its own curve, end joins and cached extents); moving only its placement origin makes the box inconsistent (measured on Snowdon Structural 2024 and rst_basic 2023). Columns and point-located instances are supported' % o['eid'])
                    if any(str(x[1]).startswith('LinearDimString') for x in ed.g.e.trace(o['eid'])[3]) or ed.g.e.trace(o['eid'])[2].get('class') == 'LinearDimString': raise EditError('element %d is a dimension: Revit does not honour a moved dimension record, so the move is refused' % o['eid'])
                    _cls = ed.g.e.trace(o['eid'])[2].get('class')
                    if _cls == 'Viewport' and os.environ.get('RVTBALLET_ENABLE_VIEWPORTMOVE') == '1': _move_viewport(ed, o); continue
                    if _cls not in MOVE_VM_VERIFIED and os.environ.get('RVTBALLET_MOVE_ANY') != '1': raise EditError('element %d is a %s: moving this class has no Revit-verified implementation (verified: %s), so the move is refused' % (o['eid'], _cls, ', '.join(sorted(MOVE_VM_VERIFIED))))
                    ed.move(o['eid'], o['dx'], o['dy'], o['dz'])
                except NotImplementedError as ne:
                    if ('class Level' in str(ne) or 'class Grid' in str(ne)) and os.environ.get('RVTBALLET_ENABLE_LEVELMOVE') == '1': _move_datum(ed, dict(o, cls='Level' if 'class Level' in str(ne) else 'Grid')); continue      # view annotations (TextNote): origin in TextElement.m_orig, 2D in the view plane
                    if 'class TextNote' not in str(ne): raise
                    if o['dz']: raise NotImplementedError('annotation move needs dz = 0')
                    if os.environ.get('RVTBALLET_ENABLE_LEADERNOTEMOVE') == '0':      # active leader (Leader.m_type != 0): Revit moves the leader end and elbow with the note (VM readback, 3 notes in 2024 and 2026: all +dx); on by default, opt-out =0
                        import struct
                        ld = {l[1]: l for l in ed.g.e.trace(o['eid'])[3]}
                        if 'Leader.m_type' in ld and struct.unpack_from('<i', _body(ed, o['eid']), ld['Leader.m_type'][2])[0] != 0: raise NotImplementedError('text note with an active leader: moving it is switched off (RVTBALLET_ENABLE_LEADERNOTEMOVE=0)')
                    ed.move_annotation(o['eid'], o['dx'], o['dy'])
            elif o['op'] == 'rotate':
                if _is_pinned(ed, o['eid']): raise EditError('element %d is pinned (Element.m_locked): rotating a pinned element is refused, as Revit does; unpin it first' % o['eid'])
                if any(str(x[1]).startswith('StructFootingUserData.') for x in ed.g.e.trace(o['eid'])[3]): raise EditError('element %d: rotate refused, it is a structural footing (StructFootingUserData / StructAttachInfo): its box does not follow the placement frame (a 1 ft move measured box shift 0 on rst_basic 2023 512451)' % o['eid'])
                if any(str(x[1]).startswith('FamInstCurveDriver.') for x in ed.g.e.trace(o['eid'])[3]): raise EditError('element %d: rotate refused, it is a curve-located family instance (beam / brace: FamInstCurveDriver with its own curve, end joins and cached extents); rotating only its placement frame makes the record inconsistent. Columns and point-located instances are supported' % o['eid'])
                ed.rotate(o['eid'], o['deg'])
                if ed.g.e.trace(o['eid'])[2].get('class') == 'SWall': WALLROT[0] = True      # isolated-wall rotate (opt-in): its record + item rewrite spans the whole element, the gate's span/budget rules for a single placement edit are widened for it only
            elif o['op'] == 'change_type': _change_type(ed, o)
            elif o['op'] == 'set_link_path': _set_link_path(ed, o)
            elif o['op'] == 'set_link_load': _set_link_load(ed, o)
            elif o['op'] == 'set_link_override': _set_link_override(ed, o)
            elif o['op'] == 'set_num': _set_num_by_pid(ed, o)
            elif o['op'] == 'set_type_num': _set_type_num(ed, a, o)
            elif o['op'] == 'set_type_eid': _set_type_eid(ed, a, o)
            elif o['op'] == 'set_type_yesno': _set_type_yesno(ed, a, o)
            elif o['op'] == 'set_type_material': _set_type_material(ed, a, o)
            elif o['op'] == 'set_room_bounding': _set_room_bounding(ed, o)
            elif o['op'] == 'set_string' and o.get('kind') == 'AString': _set_string_by_pid(ed, o)
            elif o['field'] == 'ParamValueAString.m_value': ed.set_string(o['eid'], o['match'], o['value'])
            else:
                if o['field'] in ('DatumPlane.m_text', 'DBView.m_viewName', 'SymbolInfo.m_name'): _check_element_name(o['value'])
                if o['field'] in ('DatumPlane.m_text', 'DBView.m_viewName'): _check_datum_name_unique(a, o)
                if o['field'] == 'SymbolInfo.m_name': _check_symbol_name_unique(a, o)
                ed._str_edit(o['eid'], o['field'], o['value'], o['match'])
        except (IndexError, KeyError, StopIteration, AssertionError, struct_error()) as e:
            try: _gone = o['op'] in ('move', 'rotate') and o['eid'] not in ed.g.e.m.ids
            except Exception: _gone = False
            if _gone: raise EditError('element %d does not exist in this file (deleted or never present): %s refused; nothing was changed' % (o['eid'], o['op']))
            hint = ' (the record layout of this kind of element, e.g. a group member, is not handled by the edit backend)' if o['op'] in ('move', 'rotate') else ''
            if o['op'] == 'set_string' and o.get('field') in ('DatumPlane.m_text', 'DBView.m_viewName', 'SymbolInfo.m_name'): hint = ' (this element does not have that name field: %s is only for %s, or the match text is not its current name)' % (o['field'], {'DatumPlane.m_text': 'Levels and Grids', 'DBView.m_viewName': 'views', 'SymbolInfo.m_name': 'family types'}[o['field']])
            if o['op'] == 'set_string' and o.get('field') == 'ParamValueAString.m_value': hint = ' (this element has no stored string parameter value matching that name/match text: CAD links, imports and similar elements keep none, so nothing can be set)'
            if o['op'] == 'rotate' and isinstance(e, KeyError): hint = ' (rotate is only supported for placed family instances such as columns, doors and furniture; walls, floors and annotations cannot be rotated here)'
            raise EditError('element %d: %s could not be applied (%s)%s; nothing was changed' % (o['eid'], o.get('field') or o['op'] + (' parameter %s' % o['pid'] if o.get('pid') is not None else ''), type(e).__name__, hint))
        except RuntimeError as e:        # e.g. rvtedit: 'element N lives in Partitions/X but this save edits Partitions/Y' (one partition per save)
            hint = ' (rotate is only supported for placed family instances such as columns, doors and furniture; walls, floors and annotations cannot be rotated here)' if o['op'] == 'rotate' and isinstance(e, NotImplementedError) else ''
            raise EditError('edit refused by the edit backend: %s%s' % (e, hint))
    try: ed.save(b)
    except RuntimeError as e: raise EditError('save refused by the edit backend: %s' % e)
    try:      # the members this writer actually rewrote, declared to the gate (savegate dirty_members rule): a flip in any OTHER member of the partition is then refused
        for pn, pt in ed.g.e.parts.items(): _DIRTY.d.setdefault(pn, set()).update(k for k, m in enumerate(pt.mem) if m.get('dirty'))
    except Exception: _DIRTY.d = None      # unknown: declare nothing (the gate's other checks still apply)
    for _e, _par, _kids, _dx, _dy, _dz in ed.__dict__.get('_asm_moved', []):
        for _m in [_par] + list(_kids):
            if _m != _e: ASM_MOVED.append((_m, _dx, _dy, _dz))
    return deleted


def _value_entry(log, kind, id_entry):
    """the value entry that belongs to a parameter-id entry, by exact byte contiguity. Layout (measured on 2024 records): String and Int values come directly AFTER their id, Double values directly BEFORE it
    (a value can also be contiguous with the NEXT parameter's id, so the order of the two checks matters per kind)"""
    vname = 'ParamValue%s.m_value' % kind
    after = next((x for x in log if x[1] == vname and x[2] == id_entry[3]), None); before = next((x for x in log if x[1] == vname and x[3] == id_entry[2]), None)
    return (before or after) if kind == 'Double' else (after or before)


def _set_type_num(ed, src, o):
    """overwrite the Double of ONE NamedParam (type parameter, keyed by the family parameter element id) of a FamilySymbol. Refused unless the element is a type with exactly one such entry and the parameter has no formula."""
    if os.environ.get('RVTBALLET_TYPENUM_ANY_YEAR') != '1':      # Revit-verified on 2024 only (VM probe 1379030 Slot Width); a 2022 file was accepted unchecked
        import re as _re, cfb as _cfb
        try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
        except Exception: raise EditError('type parameter edit refused: cannot read the Revit version of the file')
        if fy not in (2024, 2026): raise EditError('type parameter edit is only verified on Revit 2024/2026 files (this file is %d): refused' % fy)
    try: _mid = _field64(ed, o['eid'], 'FamilySymbol.m_masterId')
    except (IndexError, KeyError): raise EditError('element %d does not exist in this file: set_type_num refused' % o['eid'])
    if _mid is not None and _mid != 0xFFFFFFFFFFFFFFFF: raise EditError('element %d is a derived symbol of type %d (FamilySymbol.m_masterId set): edit the master type instead; nothing was changed' % (o['eid'], _mid))
    pid = o.get('pid')
    if pid is None:
        rr = os.path.expanduser('~/rvt-research')
        if rr not in sys.path: sys.path.insert(0, rr)
        import rvt_xcache, rvt_famparams as F
        cap = F.captions(rvt_xcache.get_x_ro(src)['recs']); hit = [i for i, c in cap.items() if c == o['param']]
        stored = {_eid_val(l[4]) for l in ed.g.e.trace(o['eid'])[3] if l[1] == 'NamedParam.m_paramId'}
        hit = [i for i in hit if i in stored]
        if len(hit) != 1: raise EditError('type parameter %r: %d matching entries stored on element %d (need exactly 1; give pid)' % (o['param'], len(hit), o['eid']))
        pid = hit[0]
    log = ed.g.e.trace(o['eid'])[3]; n = [k for k, l in enumerate(log) if l[1] == 'NamedParam.m_paramId' and _eid_val(l[4]) == pid]
    if len(n) != 1: raise EditError('element %d has %d NamedParam entries for parameter %d (need exactly 1; is it a type?)' % (o['eid'], len(n), pid))
    k = n[0]
    for j in range(k - 1, max(k - 12, -1), -1):
        if log[j][1] == 'NamedParam.m_value':
            try: same = float(log[j][4]) == float(o['value'])
            except (TypeError, ValueError): same = False
            if same: raise EditError('type parameter %r of element %d already has value %r: nothing to change, refused (no needless rewrite)' % (o['param'], o['eid'], o['value']))
            break
    ed.set_type_param(o['eid'], pid, o['value'])


def _set_type_material(ed, src, o):
    """assign a material to a SYSTEM type whose material is the built-in field Symbol.m_renderStyleId (spec from Revit pair c1xmatas: SysMullionFamSym 378 Material 1075 -> 751, record differs only in that 8-byte id). Target must be a MaterialElem; family types with a NamedParam material use set_type_eid."""
    import re as _re, cfb as _cfb, struct
    try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
    except Exception: raise EditError('type material edit refused: cannot read the Revit version of the file')
    if fy not in (2024, 2026): raise EditError('type material edit is only verified on Revit 2024/2026 files (this file is %d): refused' % fy)
    try: tr = ed.g.e.trace(o['eid'])
    except Exception: raise EditError('element %d does not exist; nothing was changed' % o['eid'])
    log = tr[3]; n = [l for l in log if l[1] == 'Symbol.m_renderStyleId']
    if len(n) != 1 or l_off(n[0]) is None: raise EditError('element %d has no single Symbol.m_renderStyleId material field; nothing was changed' % o['eid'])
    old = _eid_val(n[0][4])
    if old is None or old <= 0: raise EditError('element %d has no material assigned (%r); nothing was changed' % (o['eid'], n[0][4]))
    if old == o['target']: raise EditError('element %d already uses material %d' % (o['eid'], old))
    try: cls = ed.g.e.trace(o['target'])[2].get('class')
    except Exception: raise EditError('target element %d does not exist; nothing was changed' % o['target'])
    if cls != 'MaterialElem': raise EditError('target %d is a %s, not a MaterialElem: refused' % (o['target'], cls))
    if n[0][3] - n[0][2] != 8: raise EditError('unexpected material field width; nothing was changed')
    ed._rec_edit(o['eid'], [(n[0][2], 8, struct.pack('<Q', o['target']))])


def l_off(l): return l[2]


def _set_type_eid(ed, src, o):
    """re-point ONE element-id type parameter (NamedParam.m_elemId) of a FamilySymbol to another element of the same class. Spec from the Revit pair c1xeid (HVAC 2024, 'Arrow Type' 579117 -> 579118): every 8-byte id field of the record that carries the old id (the NamedParam value and the sub-instance descriptor copies) is rewritten; the writer restamps the record checksum. Refused unless exactly one NamedParam holds the pid."""
    import re as _re, cfb as _cfb, struct
    try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
    except Exception: raise EditError('type parameter edit refused: cannot read the Revit version of the file')
    if fy not in (2024, 2026): raise EditError('type parameter edit is only verified on Revit 2024/2026 files (this file is %d): refused' % fy)
    tr = ed.g.e.trace(o['eid']); log = tr[3]
    if tr[2].get('class') != 'FamilySymbol': raise EditError('element %d is not a FamilySymbol (type); nothing was changed' % o['eid'])
    _mid = _field64(ed, o['eid'], 'FamilySymbol.m_masterId')
    if _mid is not None and _mid != 0xFFFFFFFFFFFFFFFF: raise EditError('element %d is a derived symbol of type %d (FamilySymbol.m_masterId set): edit the master type instead; nothing was changed' % (o['eid'], _mid))
    n = [k for k, l in enumerate(log) if l[1] == 'NamedParam.m_paramId' and _eid_val(l[4]) == o['pid']]
    if len(n) != 1: raise EditError('element %d has %d NamedParam entries for parameter %d (need exactly 1)' % (o['eid'], len(n), o['pid']))
    k = n[0]; ev = [log[j] for j in range(max(k - 12, 0), min(k + 12, len(log))) if log[j][1] == 'NamedParam.m_elemId']
    if len(ev) != 1: raise EditError('parameter %d of element %d is not a plain element-id value; nothing was changed' % (o['pid'], o['eid']))
    old = _eid_val(ev[0][4])
    if old is None or old <= 0: raise EditError('the current value of parameter %d is not a valid element id (%r); nothing was changed' % (o['pid'], ev[0][4]))
    if old == o['target']: raise EditError('parameter %d of element %d already points at %d' % (o['pid'], o['eid'], old))
    try: t_new, t_old = ed.g.e.trace(o['target'])[2].get('class'), ed.g.e.trace(old)[2].get('class')
    except Exception: raise EditError('target element %d does not exist (or the old one is not in this file); nothing was changed' % o['target'])
    if t_new != t_old: raise EditError('target %d is a %s but the parameter currently points at a %s: refused' % (o['target'], t_new, t_old))
    try:      # c3x-rvttype: the class alone is too coarse (a Section Marks symbol is a FamilySymbol like the Elevation Marks symbol the parameter points at): the category must match too
        from . import fastquery as _fq
        z = _fq.scan(src, want_elements=True)['arrays']; ix = {int(i): k for k, i in enumerate(z['id'])}
        c_new, c_old = int(z['cat'][ix[o['target']]]), int(z['cat'][ix[old]])
    except Exception: raise EditError('type parameter edit refused: cannot read the categories of target %d and of the current value %d; nothing was changed' % (o['target'], old))
    if c_new != c_old: raise EditError('target %d has category id %d but the parameter currently points at category id %d: refused' % (o['target'], c_new, c_old))
    nb = struct.pack('<Q', o['target']); offs = {}
    for l in log:
        if l[1] in ('NamedParam.m_elemId', 'Identifier.m_id64') and l[3] - l[2] == 8:
            v = _eid_val(l[4]) if l[1] == 'NamedParam.m_elemId' else int(str(l[4]))
            if v == old: offs[l[2]] = nb
    if ev[0][2] not in offs: raise EditError('internal: the parameter value field was not located; nothing was changed')
    ed._rec_edit(o['eid'], [(off, 8, b) for off, b in sorted(offs.items())])


def _set_type_yesno(ed, src, o):
    """CREATE the never-set built-in Yes/No (Int) value 'Export Type to IFC' on a FamilySymbol. Spec from Revit pairs c1xyn8 (link type) and c1xyn9 (plain type): the null Int set pointer becomes the 6-byte class pointer and a new ParamValueSetInt [count 1][pid i64][i32] is inserted right after the Double set (or before CellList.m_cells when there is none). An existing Int set is refused (not witnessed)."""
    import re as _re, cfb as _cfb, struct, rvt_xcache
    try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
    except Exception: raise EditError('yes/no create refused: cannot read the Revit version of the file')
    if fy != 2024: raise EditError('yes/no create is only verified on Revit 2024 files (this file is %d): refused' % fy)
    tr = ed.g.e.trace(o['eid']); log = tr[3]
    if tr[2].get('class') not in ('FamilySymbol', 'SysMullionFamSym'): raise EditError('element %d is not a type symbol (class %s); nothing was changed' % (o['eid'], tr[2].get('class')))
    L = {l[1]: l for l in log}
    ptr = L.get('Element.m_pParamValueSetInt'); dbl = L.get('ParamValueSetDouble.m_paramSet'); cl = L.get('CellList.m_cells')
    if 'ParamValueSetInt.m_paramSet' in L: raise EditError('element %d already has an Int value set: editing it is not Revit-witnessed; nothing was changed' % o['eid'])
    if not ptr or ptr[3] - ptr[2] != 4 or bytes(ed.g.bj[ptr[2]:ptr[3]]) != b'\0\0\0\0' or not (dbl or cl): raise EditError('element %d has no known place to create an Int set; nothing was changed' % o['eid'])
    tag = None
    for k2 in rvt_xcache.get_x(src)['recs']:
        e2 = k2[0] if isinstance(k2, tuple) else k2
        try: l2 = {l[1]: l for l in ed.g.e.trace(e2)[3]}.get('Element.m_pParamValueSetInt')
        except Exception: continue
        if l2 and l2[3] - l2[2] == 6: tag = bytes(ed.g.bj[l2[2]:l2[3]]); break
    if not tag: raise EditError('no element carries an Int set pointer to copy the class tag from; nothing was changed')
    at = dbl[3] if dbl else cl[2]
    ed._rec_edit(o['eid'], [(ptr[2], 4, tag), (at, 0, struct.pack('<IQi', 1, o['pid'] % (1 << 64), o['value']))])


def _check_wall_height_pid(o, pid, log):
    """c3x-rvtmatrix 2026-11-14 (Revit VM, 2024 Structural wall): the reader names pid -1001105 'Unconnected Height', but a wall that also stores -1001101 reads its Unconnected Height from THAT value in Revit; writing -1001105 saved cleanly, passed the offline read-back and was ignored by Revit (76.75 stayed). Refused until the VM settles which id is the live one."""
    if pid == -1001105 and o.get('kind') == 'Double' and any(l[1] == 'ParamValueDouble.m_paramId' and _eid_val(l[4]) == -1001101 for l in log):
        raise EditError('Unconnected Height on element %d is stored under two ids (-1001105 and -1001101) and Revit reads the other one: an edit of the first is ignored by Revit; refused (give pid -1001101 explicitly); nothing was changed' % o['eid'])


_SETNUM_GEOM_CLASSES = ('Floor', 'SWall', 'ArcWall', 'Wall')


def _setnum_geom_class(cls):
    """Floors, walls, ceilings and roofs (any class name containing Ceiling or Roof): their offset/thickness/fascia numbers drive stored geometry (c4x-rvtdiff 2026-11-16: floor and wall verified stale in the Revit VM; ceiling and roof by analogy, ledger PASS rows compared only the parameter readback)"""
    if cls.endswith(('Type', 'Attributes', 'Attr', 'Sym')): return False      # type/attribute elements are edited through the type ops (set_type_num, VM-verified), not here
    return cls in _SETNUM_GEOM_CLASSES or any(k in cls for k in ('Ceiling', 'Roof', 'Wall', 'Sweep', 'Floor', 'Railing'))      # SweepHost (wall sweeps/reveals: offsets), CurtainWall, ProfileRoof, ...: instance classes found by the Double-storing class scan of Structural/Facades 2024      # classes whose Double parameters drive stored geometry that Revit regenerates


def _set_num_by_pid(ed, o):
    """overwrite the stored Double/Int value of ONE parameter (exact entry, not rvtedit.set_num's 'previous value within 8 entries', which edits the neighbouring Int for every Int but the first)"""
    import struct
    pid = _resolve_pid(ed, o); log = ed.g.e.trace(o['eid'])[3]
    _check_wall_height_pid(o, pid, log)
    if o.get('kind') == 'Int' and (ed.g.e.trace(o['eid'])[2].get('class') or '') == 'Level':      # c1x-rvttype 2026-11-16 (Revit 2024 pair c1xlvl3, Structural Level 329 Building Story Yes -> No: the Level record is unchanged, element 13 grows by 20 bytes and 2 id tables change): not an in-place int patch
        raise EditError('element %d is a Level: its integer parameters (e.g. Building Story) are stored outside the level record (Revit grows element 13 and updates id tables), a bare write would not match; refused, nothing was changed' % o['eid'])
    if o.get('kind') == 'Double' and os.environ.get('RVTBALLET_SETNUM_GEOM') != '1' and _setnum_geom_class(ed.g.e.trace(o['eid'])[2].get('class') or ''):      # c4x-rvtdiff 2026-11-16 (walls: Revit VM elemhash, Structural 2024 wall 585072 Top Offset 0 -> 2: Unconnected Height reads 78.75 but Area 780.29 and Volume 645.19 are unchanged) (Revit VM, Snowdon Structural 2024 floor 621720 Height Offset From Level 0 -> 1.5): the saved file reads Height Offset 1.5 but Elevation at Bottom/Top stay 5.0/5.5 (a Revit-made change gives 6.5/7.0: Floor.m_bottom/m_top and 5 Plane.m_origin shift with the parameter); a bare parameter write leaves stale geometry
        raise EditError('element %d is a floor, wall, ceiling or roof: its offset/dimension parameters drive stored geometry (Floor.m_bottom/m_top and the sketch planes) that Revit regenerates; a bare parameter write leaves the geometry at the old position, so it is refused (RVTBALLET_SETNUM_GEOM=1 to force); nothing was changed' % o['eid'])
    for l in log:
        if l[1] == 'ParamValue%s.m_paramId' % o['kind'] and _eid_val(l[4]) == pid:
            vn = _value_entry(log, o['kind'], l)
            if vn is None: break
            nb = struct.pack('<d' if o['kind'] == 'Double' else '<i', o['value'])
            if len(nb) != vn[3] - vn[2]: raise AssertionError('value size mismatch')
            ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('param %d (%s) not stored on %d' % (pid, o['kind'], o['eid']))


NAME_FORBIDDEN = set('\\:{}[]|;<>?`~')


def _nk(x):
    return __import__('unicodedata').normalize('NFC', x.strip()).casefold()      # c5x-rvtread: NFC and NFD spellings of one name are duplicates


def _check_element_name(v):
    """Revit refuses empty names and names with any of \\ : { } [ ] | ; < > ? ` ~ for levels, grids, views and types; the writer used to save them (c5x-rvtread)"""
    bad = sorted(set(v) & NAME_FORBIDDEN)
    if not v.strip(): raise EditError('a name must not be empty; nothing was changed')
    if v != v.strip(): raise EditError('a name must not start or end with a space (Revit trims or rejects it, not VM-verified); nothing was changed')
    if set(v) == {'.'}: raise EditError('a name made only of dots is refused (Revit behaviour unverified); nothing was changed')
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in v): raise EditError('a name must not contain control characters (newline, tab, ...); nothing was changed')
    if any(__import__('unicodedata').category(ch) in ('Cs', 'Zl', 'Zp', 'Co', 'Cn') for ch in v): raise EditError('a name must not contain lone surrogates, line/paragraph separators or unassigned/private-use characters; nothing was changed')      # lone surrogate cannot be encoded as UTF-16 at all
    if any(__import__('unicodedata').category(ch) == 'Cf' for ch in v): raise EditError('a name must not contain invisible format characters (BOM, zero-width, bidi override); nothing was changed')      # c5x-rvtread: spoofing/duplicate-lookalike names; Revit VM verdict on these not taken, refusal is conservative
    if any(ord(ch) > 0xFFFF for ch in v): raise EditError('characters outside the Basic Multilingual Plane (emoji, rare CJK) are not supported in names yet (same rule as string values); nothing was changed')
    if len(v) > 255: raise EditError('a name is limited to 255 characters here (conservative; Revit limits are not VM-verified above that); nothing was changed')
    if bad: raise EditError('name contains characters Revit does not allow in names (%s); nothing was changed' % ' '.join(bad))


def _check_batch_names(ops):
    """two renames of one batch onto the same name (same field, case-insensitive) would create a duplicate that the per-op check on the source cannot see (c5x-rvtread); conservative: also refuses a Level and a Grid sharing a name"""
    seen = {}
    for o in ops:
        if o.get('op') == 'set_string' and o.get('field') in ('DatumPlane.m_text', 'DBView.m_viewName') and o.get('pid') is None:
            k = (o['field'], _nk(o['value']))
            if k in seen and seen[k] != o['eid']: raise EditError('elements %d and %d would get the same name %r in one save: Revit does not allow duplicate names; nothing was changed' % (seen[k], o['eid'], o['value']))
            seen[k] = o['eid']


def _check_datum_name_unique(src, o):
    """Revit does not allow two Levels, two Grids or two views of one kind with the same name (case-insensitive): refuse a rename onto a sibling's name (c5x-rvtread; the writer used to save it). Views: same class (DBViewPlan, DBViewSection, ...), conservative"""
    import rvt_entities
    fld, pre = ('m_viewName', ('DBView',)) if o['field'] == 'DBView.m_viewName' else ('m_text', ('Level', 'Grid'))
    r = rvt_entities.extract(src, slim=lambda c: c.startswith(pre))
    mine = [k for k in r['recs'] if k[0] == o['eid'] and k[1].startswith(pre)]
    if not mine: return
    new = _nk(o['value'])
    for k, v in r['recs'].items():
        if k[1] == mine[0][1] and k[0] != o['eid'] and _nk(str(v.get('fields', {}).get(fld, ''))) == new:
            raise EditError('a %s named %r already exists (element %d): Revit does not allow duplicate names; nothing was changed' % (k[1], o['value'], k[0]))


def _check_symbol_name_unique(src, o):
    """Revit does not allow two types of one family with the same name (case-insensitive): refuse a type rename onto a sibling's name (c5x-rvtread item 20). Uses the reader's FamilySymbol 'Type Name'/'Family Name'; when the reader does not expose that symbol (2024 template, other classes) nothing is checked here."""
    import sys, os
    for pth in ('~/rvt-research', '~/rvt-research/write-lab'):
        if os.path.expanduser(pth) not in sys.path: sys.path.insert(0, os.path.expanduser(pth))
    try:
        from . import save as _sv; P = _sv._read_params(open(src, 'rb').read())
    except Exception: return
    me = P.get(o['eid'])
    if not isinstance(me, dict) or me.get('class') != 'FamilySymbol': return
    fam = (me.get('params') or {}).get('Family Name')
    if fam is None: return
    new = _nk(o['value'])
    for e, d in P.items():
        if e != o['eid'] and isinstance(d, dict) and d.get('class') == 'FamilySymbol':
            q = d.get('params') or {}
            if q.get('Family Name') == fam and _nk(str(q.get('Type Name', ''))) == new:
                raise EditError('type %r already exists in family %r (element %d): Revit does not allow duplicate type names; nothing was changed' % (o['value'], fam, e))


def _full_astr(ed, vn):
    """full text of an AString value entry (the decoder trace keeps only str(value)[:60]); falls back to the 60-char preview when the bytes do not decode as count + UTF-16"""
    import struct
    try:
        n = struct.unpack_from('<I', ed.g.bj, vn[2])[0]
        if vn[3] - vn[2] == 4 + 2 * n: return bytes(ed.g.bj[vn[2] + 4:vn[3]]).decode('utf-16le')
    except Exception: pass
    return vn[4]


_CREATE_BIP = {'Comments': -1010106, 'Mark': -1001203}      # built-in ids as Revit 2024 reported them in the creation witnesses (c4xcm1/cm2 Comments, c4xcm10 Mark)


def _create_astring(ed, o):
    """c4x-rvtmatrix items 141-154: create the never-set string parameter Comments the way Revit does (3 byte-exact Revit witnesses, Revit 2024 + 2026 VM open and readback). The element's null Element.m_pParamValueSetAString pointer becomes ffffffff + u16 tag (tag = the single value shared by all AString sets of the file), and a set object (u32 1, i64 id, u32 nchars, UTF-16) is inserted after the Double/Int set objects. Refused: an element that already has a string set, one without a Double/Int set (no witnessed anchor), one with an ElementId set (order not witnessed), a file without exactly one tag."""
    import struct, collections, rvt_xcache
    if not o['value']: raise EditError('element %d: creating %s with an empty value is not supported (Revit never stores an empty new string parameter; witnesses used non-empty text); nothing was changed' % (o['eid'], o['param']))
    log = ed.g.e.trace(o['eid'])[3]
    ptr = [l for l in log if l[1] == 'Element.m_pParamValueSetAString']
    if len(ptr) != 1 or bytes(ed.g.bj[ptr[0][2]:ptr[0][3]]) != b'\0\0\0\0': raise EditError('element %d: cannot create parameter Comments (it already has string parameters or the layout is not the witnessed one); nothing was changed' % o['eid'])
    sets = {l[1][len('ParamValueSet'):-len('.m_paramSet')]: l for l in log if l[1].startswith('ParamValueSet') and l[1].endswith('.m_paramSet')}
    before = [sets[n] for n in ('Double', 'Int') if n in sets]
    if not before or 'ElementId' in sets: raise EditError('element %d: creating Comments is only supported on elements with a Double or Int parameter set and no ElementId set (the only layouts Revit witnessed); nothing was changed' % o['eid'])
    c = collections.Counter()
    for k, r in rvt_xcache.get_x(ed.src)['recs'].items():
        v = (r.get('fields') or {}).get('m_pParamValueSetAString')
        if isinstance(v, dict) and v.get('handle') == 4294967295 and 'ptr' in v: c[v['ptr']] += 1
    if len(c) != 1: raise EditError('cannot create parameter Comments: the file has %d distinct string-set tags (need exactly 1); nothing was changed' % len(c))
    body = struct.pack('<I', 1) + struct.pack('<q', _CREATE_BIP[o['param']]) + struct.pack('<I', len(o['value'])) + o['value'].encode('utf-16le')
    ed._rec_edit(o['eid'], [(ptr[0][2], 4, b'\xff\xff\xff\xff' + struct.pack('<H', next(iter(c)))), (max(l[3] for l in before), 0, body)])


def _set_string_by_pid(ed, o):
    """overwrite the string value that belongs to ONE parameter id (exact log entry), not 'the first value with this text'"""
    import struct
    try: pid = _resolve_pid(ed, o)
    except EditError:
        if os.environ.get('RVTBALLET_CREATE_ASTRING') == '1' and o.get('pid') is None and o.get('param') in _CREATE_BIP and not o.get('expect'): _create_astring(ed, o); return      # opt-in, default stays a refusal
        raise
    log = ed.g.e.trace(o['eid'])[3]
    for k, l in enumerate(log):
        if l[1] == 'ParamValueAString.m_paramId' and _eid_val(l[4]) == pid:
            # the value entry is the one whose bytes are CONTIGUOUS with this id entry (directly after, else directly before): never 'the nearest value' (that picked the neighbouring parameter)
            vn = _value_entry(log, 'AString', l)
            if vn is None: break
            if o.get('expect') is not None and _full_astr(ed, vn) != str(o['expect']): raise EditError('element %d parameter is %r, not the expected %r: nothing was changed' % (o['eid'], vn[4], o['expect']))      # stale expected value (c3x-rvttype)
            if _full_astr(ed, vn) == str(o['value']): raise EditError('element %d: parameter already has the value %r; nothing to change, nothing was written' % (o['eid'], o['value']))      # c4x-rvtdiff 199: was a bare gate refusal (not_applied)
            nb = struct.pack('<I', len(o['value'].encode('utf-16le')) // 2) + o['value'].encode('utf-16le'); ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('string parameter %d not stored on %d' % (pid, o['eid']))


UNIQUE_CLASS = __import__('re').compile(r'(Tracker|Tracking(Elem|Element)?|Settings?(Elem|Element)?|Table|Manager|Navigator|Library|Cache|Lock)$|^AllProject|^ProjectInfo|^Units')      # singleton-style classes; evidence: AllProjectRevisions delete -> Revit repair dialog (c7x-rvtmatrix, 2024 VM)


WALLROT = [False]      # set by _rvtedit_pass when an isolated SWall was rotated (c1x-rvtmove 2026-11-15)
MOVE_VM_VERIFIED = {'FamilyInstance', 'ImportInstance', 'TextNote', 'Level', 'Grid'}      # classes whose move was opened in the Revit VM with a matching API readback (ledger rung 1); ImportInstance incl. a PINNED link (Pinned is not stored in the record: 3rd Revit 2024 open clean, bbox +1 X, pinned kept); anything else with an origin field (groups, stairs, imports, masses ...) would move without its dependents: refused 
DELETE_VM_VERIFIED = {'CategoryElem', 'BasePoint', 'BrowserOrganization', 'SWall', 'ColorFillSchema', 'Floor', 'CompoundCeilingType', 'DBViewPlan', 'AutoJoinTracker', 'AssemblyCodeTable', 'Viewport', 'DimensionStyle', 'RoomElem', 'FamilyInstance', 'TextNote', 'IndependentTag', 'RoomTag', 'ScheduleInstance', 'DBViewSchedule'}      # Revit 2024 VM, single-element delete on the cols2 scene: opens with no repair prompt (SWall: only Revit's own 'Room is not in a properly enclosed region' warning, the true consequence of removing a bounding wall) (c7x-rvtmatrix); RoomElem clean in VM too; FamilyInstance/TextNote/IndependentTag/RoomTag/ScheduleInstance/DBViewSchedule opened clean in the Revit 2024 VM on Snowdon HVAC and Structural (c1x-rvtdel, class-count dumps exact, FamilyInstance cascade took its tags); DBDrawing (sheet) REMOVED again: delete leaves the sheet's Viewport with m_dbDrawingId pointing at the deleted sheet (dangling; Revit cascades the viewport), the VM open compare did not see it; extend only with a VM verdict


IN_USE_GUARD_CLASSES = {'DimensionStyle', 'CompoundCeilingType', 'AssemblyCodeTable'}      # type-like classes whose users are not in the header deletion lists
IN_USE_GUARD_ALLOW = 5      # measured: an id occurs 5 times more in the file before delete than after (own record + lists), Structural 2024 DimensionStyle/CategoryElem/CompoundCeilingType


def tags_hosting(ed, eid):
    """ids of IndependentTag elements whose host reference (RoomBoundingItem.m_linkInstOrHostId) is eid (the tag is not in the host's deletion list). Reads the decoded records of the reader cache (rvt_xcache), no per-element trace."""
    import rvt_xcache
    needle = 'EID(%d)' % int(eid); out = []
    for key, rec in rvt_xcache.get_x(ed.src)['recs'].items():
        if key[1] == 'IndependentTag' and needle in str(rec.get('fields')): out.append(int(key[0]))
    return sorted(out)

def _delete(ed, eid):
    """delete with what Revit's Delete removes: class-specific paths of rvtedit (floor / view / sheet), else owned_set; returns every deleted id (they all go in the manifest)"""
    try: cls = ed.g.e.trace(eid)[2]['class']
    except (IndexError, KeyError, StopIteration): raise EditError('element %d does not exist in this file (no record with that id); nothing was changed' % eid)
    if os.environ.get('RVTBALLET_DELETE_ANY') != '1' and cls not in DELETE_VM_VERIFIED:
        raise EditError('element %d is a %s: delete is only enabled for classes whose output was opened in Revit without a repair prompt (%s); other classes are refused (override for experiments: RVTBALLET_DELETE_ANY=1)' % (eid, cls, ', '.join(sorted(DELETE_VM_VERIFIED))))
    if os.environ.get('RVTBALLET_DELETE_ANY') != '1':      # year gate: the whitelist is 2024-verified; 2026 verified only for SWall/FamilyInstance/Floor (Revit 2026 VM open clean) and IndependentTag (VM open clean + API readback: 1 id gone, 0 others changed; c3x-rvtdel); other years never gated
        import re as _re, cfb as _cfb
        try: fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(ed.src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
        except Exception: raise EditError('delete refused: cannot read the Revit version of the file')
        if fy != 2024 and not (fy == 2026 and cls in ('SWall', 'FamilyInstance', 'Floor', 'IndependentTag')) and not (fy == 2025 and cls in ('SWall', 'FamilyInstance')): raise EditError('delete of a %s is not VM-verified on Revit %d files (verified: 2024; 2025 only SWall/FamilyInstance, ledger PASS rows Snowdon Structural column/beam/wall and Facades window, Revit 2025 VM open clean + readback; 2026 only SWall/FamilyInstance/Floor/IndependentTag): refused, nothing changed' % (cls, fy))
    if cls not in DELETE_VM_VERIFIED and UNIQUE_CLASS.search(cls): raise EditError('element %d is a %s: a project-wide settings / tracker / table element that Revit expects to exist exactly once (deleting AllProjectRevisions made Revit show "Repair Missing Unique Elements"); not deleted' % (eid, cls))
    if cls == 'RoomElem' and os.environ.get('RVTBALLET_DELETE_ROOM_TAGGED') != '1':
        # c1x-rvtdel item 114: after a room delete the room's RoomTag(s) and the LevelRoomPlan still hold its id (dangling, measured Structural 2024 room 583143: RoomTag 583144, LevelRoomPlan 582607); Revit's own cascade for tags is not verified, so tagged rooms are refused
        import rvt_xcache, re as _re
        needle = 'EID(%d)' % int(eid); tg = [int(k2[0]) for k2, r2 in rvt_xcache.get_x(ed.src)['recs'].items() if k2[1] == 'RoomTag' and needle in str(r2.get('fields'))]
        if tg: raise EditError('room %d is tagged by RoomTag %s: a room delete would leave those tags pointing at a missing room (Revit cascade not reproduced); nothing was changed' % (eid, tg[:5]))
    if cls == 'SWall' and os.environ.get('RVTBALLET_DELETE_WALL_JOINED') != '1':
        # c1x-rvtdel item 119: paired Revit Delete(1139388) on Structural/Site 2024 rewrote the joined neighbour wall (EndInfo/CDJoinInfo join entry cleared, face history regenerated); our delete left that join entry naming the removed wall. Walls still named by another SWall (joins) are refused until the neighbour patch is reproduced.
        import rvt_xcache
        needle = 'EID(%d)' % int(eid); nb = [int(k2[0]) for k2, r2 in rvt_xcache.get_x(ed.src)['recs'].items() if k2[1] in ('SWall', 'Floor', 'VarSketch', 'CurveElem', 'BaseRailing', 'LinearDimString') and int(k2[0]) != int(eid) and needle in str(r2.get('fields')) and int(k2[0]) not in getattr(ed, '_deleted_ids', ())]
        if nb: raise EditError('wall %d is still named by element(s) %s whose join data or sketch/boundary geometry still names it: Revit rewrites those elements on delete (join entry cleared, geometry regenerated) and this editor cannot reproduce that; nothing was changed' % (eid, nb[:5]))
    if cls == 'FamilyInstance':
        # c4x-rvtmatrix item 53 (ESCAPE): deleting a Title Blocks instance owned by a drafting view (Element.m_ownerDBViewId = DBViewDrafting) on the 2026 HVAC sample was accepted (gate 0 diffs, our reader saw 1 element gone) but Revit's API readback of the output showed 9 fewer elements (title block, ViewSchedule, ScheduleSheetInstance, GraphicsStyle, 5 uncategorised). View-owned instances (title blocks, detail components, annotation symbols) are refused until their delete is reproduced exactly; model instances (no owner view; Structural 2024 588559 measured exactly -1 in Revit) stay allowed.
        import re as _re
        for l in ed.g.e.trace(eid)[3]:
            if l[1] == 'Element.m_ownerDBViewId':
                m = _re.search(r'(\d+)', str(l[4])); ov = int(m.group(1)) if m else None
                if ov is not None and ov < 2 ** 62:
                    try: oc = ed.g.e.trace(ov)[2]['class']
                    except Exception: oc = '?'
                    raise EditError('element %d belongs to a view (owner %s %d: a title block, detail component or annotation symbol): deleting it makes Revit also drop dependent elements (a schedule and related records were lost in the Revit readback of a measured 2026 delete) that this editor cannot reproduce; nothing was changed' % (eid, oc, ov))
                break
    if cls == 'FamilyInstance' and os.environ.get('RVTBALLET_DELETE_HOSTED') != '1' and not any(l[1] == 'FamilyInstance.m_superInstanceId' and 0 < (int(__import__('re').findall(r'\d+', str(l[4]))[0]) if __import__('re').findall(r'\d+', str(l[4])) else 0) < 2 ** 62 for l in ed.g.e.trace(eid)[3]):      # nested children are refused by the membership check below with its own message
        # c4x-rvtdiff 151 (ESCAPE): deleting a window hosted in a wall was accepted (gate 0 diffs, Facades 2024 593207) but Revit-made delete (witness c4x_wdel1) also regenerates the host walls (cutout list, face/edge history, record lengths -1.2/-2.4 KB) and a dimension; the writer leaves the walls stale
        import re as _re
        for l in ed.g.e.trace(eid)[3]:
            if l[1] in ('InsertableInst.m_hostId', 'InsertableInst.m_extraHostIds'):
                for hid in (int(x) for x in _re.findall(r'\d+', str(l[4]))):
                    if 0 < hid < 2 ** 62:
                        try: hc = ed.g.e.trace(hid)[2]['class']
                        except Exception: hc = '?'
                        try: _cat = ed._category(ed.g.template(eid))
                        except Exception: _cat = None
                        if _cat is None:      # 2026 files: g.template has no header for the id (IndexError); the reader's header table carries the category (ElementHeader.m_categroryId)
                            try:
                                import rvt_xcache, re as _re2
                                _m = _re2.search(r'(\d+)', str(rvt_xcache.get_x_ro(ed.src)['eh'][eid]['m_categroryId']))
                                if _m: _cat = int(_m.group(1)) - (1 << 64) if int(_m.group(1)) >= (1 << 63) else int(_m.group(1))
                            except Exception: _cat = None
                        if hc == 'SWall' and _cat in (-2000014, -2000023): continue      # c4x-rvtdiff 153: Windows/Doors in a straight wall: Revit regenerates the wall on open and its API Area/Volume of both host walls of Facades 2024 593207 equal the Revit-made delete (VM probes wp2_*), 2025/2026 ledger PASS rows
                        if hc != 'Level': raise EditError('element %d is hosted in a %s (%d): Revit regenerates the host geometry when a hosted instance is deleted (wall cutout and face history records are rewritten) and this editor cannot reproduce that; nothing was changed' % (eid, hc, hid))
    if cls not in ('IndependentTag', 'ViewSheet') and not cls.startswith('DBView'):
        # c4x-rvtmatrix item 81: a tag points at its host through RoomBoundingItem.m_linkInstOrHostId and is NOT in the host's deletion list, so owned_set/cascade never saw it. 2025 Structural column delete (606331) was accepted (gate 0 diffs) and left Tag 869338 dangling; Revit dropped the tag on open (readback 2 elements gone, not 1). Refuse while a tag still names the element.
        tg = [t for t in tags_hosting(ed, eid) if t not in getattr(ed, '_deleted_ids', ())]      # a tag deleted earlier in the same batch is not dangling
        if tg: raise EditError('element %d is the host of %d tag(s) (%s): deleting it would leave dangling tag references (Revit removes the tags itself on open, so the saved file would differ from what was requested); delete the tags first. Nothing was changed' % (eid, len(tg), ', '.join(map(str, tg[:5]))))
    if cls in IN_USE_GUARD_CLASSES:
        # a type/style that other elements still reference: Structural 2024 DimensionStyle 908160 is used by 12 dimensions, the old delete removed only its own record (1 id) and left 12 dangling type refs (escape). Revit refuses or cascades; we refuse.
        import re as _re
        w = ed.g.W; pat = _re.escape(int(eid).to_bytes(w, 'little')); n = sum(len(_re.findall(pat, p['joined'])) for p in ed.g.e.m.parts.values())
        if n > IN_USE_GUARD_ALLOW: raise EditError('element %d is a %s still referenced by other elements (%d occurrences of its id in the element streams, own record and id lists account for at most %d): deleting it would leave dangling references; nothing was changed' % (eid, cls, n, IN_USE_GUARD_ALLOW))
    if cls == 'Floor' and os.environ.get('RVTBALLET_DELETE_FLOOR_WALLREF') != '1':
        # c1x-rvtdel item 120: Site 2024 floor 1139521 is still named by walls 1139388/1139389 (field scan); a Revit-made wall delete rewrote exactly such a neighbour (join data, regenerated geometry), so a floor named by a wall is refused until a paired Revit floor delete shows the neighbour patch
        import rvt_xcache
        needle = 'EID(%d)' % int(eid); nb = [int(k2[0]) for k2, r2 in rvt_xcache.get_x(ed.src)['recs'].items() if k2[1] == 'SWall' and needle in str(r2.get('fields')) and int(k2[0]) not in getattr(ed, '_deleted_ids', ())]
        if nb: raise EditError('floor %d is still named by wall(s) %s: Revit rewrites such walls when the floor goes and this editor cannot reproduce that; nothing was changed' % (eid, nb[:5]))
    if cls == 'Floor':
        # delete_floor looks up the class of every candidate id with a full record decode (about 60 s each on a big file, the same ids many times: 1590 s of a 1676 s two-delete save, profiled); cache those read-only lookups until the first real deletion
        tr0 = ed.g.e.trace; memo = {}
        def tr(x, *a, **k):
            if a or k: return tr0(x, *a, **k)
            if x not in memo: memo[x] = tr0(x)
            return memo[x]
        d0 = ed.delete
        def dele(*ids):
            ed.g.e.trace = tr0; ed.delete = d0; return d0(*ids)      # no cache once records change
        ed.g.e.trace = tr; ed.delete = dele
        try: return list(ed.delete_floor(eid))
        finally: ed.g.e.trace = tr0; ed.delete = d0
    if cls.startswith('DBView') and cls not in ('DBViewType',):
        if any(l[1] == 'DBView.m_isTemplate' and str(l[4]).strip() in ('1', 'True') for l in ed.g.e.trace(eid)[3]):      # Structural 2024 template 780021 was deleted (2 ids) while dozens of views carry DBView.m_viewTemplateId = 780021: dangling template refs (escape)
            raise EditError('element %d is a view template: views may still use it (DBView.m_viewTemplateId) and deleting it would leave dangling references; nothing was changed' % eid)
        return list(ed.delete_view(eid))
    if cls == 'ViewSheet': return list(ed.delete_sheet(eid) or [eid])
    if cls == 'DBDrawing':      # c1x-rvtdel item 122: Revit-made Delete of Structural 2024 sheet 251 removes {248 DBViewProject, 249 Viewer, 250 Viewport, 251} and nothing else; the generic path removed only 251 and left the Viewport dangling
        ids = sorted(ed.cascade(eid)); ed.delete(*ids); return ids
    ids = ed.owned_set(eid); ed.delete(*ids); return list(ids)


def struct_error():
    import struct
    return struct.error
