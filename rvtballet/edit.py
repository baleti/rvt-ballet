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


def validate_op(op):
    if not isinstance(op, dict) or op.get('op') not in ('set_string', 'set_num', 'delete', 'move', 'rotate', 'change_type'): raise EditError('unsupported edit op (supported: set_string, set_num, delete, move, rotate)')
    if not isinstance(op.get('eid'), int) or isinstance(op.get('eid'), bool): raise EditError('eid (element id) must be an integer')
    if not 0 <= op['eid'] < 2 ** 63: raise EditError('eid (element id) is out of range')
    if op['op'] == 'move':
        if BACKEND() != 'rvtedit': raise EditError('move needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        d = [op.get(k, 0.0) for k in ('dx', 'dy', 'dz')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 5e4 for v in d): raise EditError('dx, dy, dz must be finite numbers (Revit internal units = feet), |v| <= 50000 (Revit keeps geometry within about 20 miles = 105600 ft of the origin)')
        if not any(d): raise EditError('move by zero')
        return {'op': 'move', 'eid': op['eid'], 'dx': float(d[0]), 'dy': float(d[1]), 'dz': float(d[2])}
    if op['op'] == 'change_type':
        if os.environ.get('RVTBALLET_ENABLE_CHANGETYPE') != '1': raise EditError('change_type is disabled (opt-in: RVTBALLET_ENABLE_CHANGETYPE=1; no Revit evidence for it yet)')
        if BACKEND() != 'rvtedit': raise EditError('change_type needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        t = op.get('type_eid')
        if not isinstance(t, int) or isinstance(t, bool) or not 0 <= t < 2 ** 63: raise EditError('type_eid (the FamilySymbol element id) must be an integer')
        return {'op': 'change_type', 'eid': op['eid'], 'type_eid': t}
    if op['op'] == 'rotate':
        if BACKEND() != 'rvtedit': raise EditError('rotate needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        d = op.get('deg')
        if isinstance(d, bool) or not isinstance(d, (int, float)) or d != d or abs(d) > 360: raise EditError('deg must be a finite number of degrees, |deg| <= 360')
        if d % 360 == 0: raise EditError('rotate by a multiple of 360 degrees changes nothing')
        return {'op': 'rotate', 'eid': op['eid'], 'deg': float(d)}
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
        pid, cands = _param_spec(op)
        if BACKEND() != 'rvtedit': raise EditError('set_num needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        return {'op': 'set_num', 'eid': op['eid'], 'pid': pid, 'pids': cands, 'param': op.get('param'), 'value': float(v) if kind == 'Double' else int(v), 'kind': kind}
    if not isinstance(op.get('value'), str): raise EditError('value must be a string')
    if op.get('param') is not None or op.get('pid') is not None:       # address the parameter by NAME/ID instead of by old text (several string parameters can hold the same text)
        if BACKEND() != 'rvtedit': raise EditError('editing a parameter by name or id needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        pid, cands = _param_spec(op)
        _check_text(op['value'])
        return {'op': 'set_string', 'eid': op['eid'], 'field': 'ParamValueAString.m_value', 'value': op['value'], 'match': None, 'pid': pid, 'pids': cands, 'param': op.get('param'), 'kind': 'AString'}
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
        elif o['op'] == 'change_type': k = ('change_type', e)      # the last type wins
        if k is None: out.append(o); continue
        if k in slot:
            i = slot[k]
            if o['op'] == 'move': out[i] = dict(out[i], dx=out[i]['dx'] + o['dx'], dy=out[i]['dy'] + o['dy'], dz=out[i]['dz'] + o['dz'])
            elif o['op'] == 'rotate': out[i] = dict(out[i], deg=out[i]['deg'] + o['deg'])
            else: out[i] = o
        else: slot[k] = len(out); out.append(dict(o))
    keep = []
    for o in out:
        if o['op'] == 'move' and max(abs(o['dx']), abs(o['dy']), abs(o['dz'])) < 1e-12: continue
        if o['op'] == 'rotate' and abs(math.remainder(o['deg'], 360.0)) < 1e-9: continue
        keep.append(o)
    return keep


def apply(buf, ops): return apply_full(buf, ops)[0]


_DIRTY = __import__('threading').local()      # per thread: {partition stream: set(member idx)} the writer rewrote during the last apply_full (None = could not be determined)


def last_dirty_members():
    d = getattr(_DIRTY, 'd', None)
    return None if d is None else {k: sorted(v) for k, v in d.items()}


def apply_full(buf, ops):
    """replay ops on bytes -> new bytes (the source bytes are never modified). Backend: env RVTBALLET_EDIT_BACKEND = wledit (default) | rvtedit"""
    ops = compose(ops); _DIRTY.d = {}
    if not ops: return buf, []
    d = tempfile.mkdtemp(prefix='rvtballet-edit-'); a = os.path.join(d, 'in.rvt'); b = os.path.join(d, 'out.rvt')
    try:
        with open(a, 'wb') as f: f.write(buf)
        deleted = (_apply_rvtedit if BACKEND() == 'rvtedit' else _apply_wledit)(a, b, ops) or []
        with open(b, 'rb') as f: return f.read(), deleted
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)      # everything in it, including intermediate pass files of a failed multi-partition run


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
                    if o['op'] == 'rotate' and pn != probe.g.e.trace(o['eid'])[0]:      # older copy elsewhere: the reader sees the OLD copy, so the rotation could not be verified (QUEUE 59e)
                        raise EditError('element %d has records in several partitions (the edit would go to the newest copy, which the viewer cannot read back): rotate refused' % o['eid'])
                except EditError: raise
                except Exception: pn = None
                groups.setdefault(pn, []).append(o)
            del probe
            if len(groups) > 1 and any(o['op'] == 'delete' for o in ops): raise EditError('a delete cannot be saved together with edits in other partitions of this file (the order across partitions is not preserved): save the delete separately')
        else: groups[None] = list(ops)
        deleted = []; cur = a
        for n, (pn, grp) in enumerate(groups.items()):
            last = n == len(groups) - 1; out = b if last else os.path.join(os.path.dirname(b), 'pass%d.rvt' % n)
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


def _field64(ed, eid, name):
    import struct
    for l in ed.g.e.trace(eid)[3]:
        if l[1] == name and l[3] - l[2] == 8: return struct.unpack_from('<Q', ed.g.bj, l[2])[0]
    return None


def _change_type(ed, o):
    """point a FamilyInstance at another FamilySymbol of the SAME family: overwrite FamilyInstance.m_masterSymbolId (8-byte ElementId) in the instance record. Refused unless the instance has that field, the target has FamilySymbol.m_familyId, and both families are equal (a symbol of another family would need a different geometry / host relation)"""
    cur = _field64(ed, o['eid'], 'FamilyInstance.m_masterSymbolId')
    if cur is None: raise EditError('element %d is not a family instance (no FamilyInstance.m_masterSymbolId): change_type refused' % o['eid'])
    fam_new = _field64(ed, o['type_eid'], 'FamilySymbol.m_familyId')
    if fam_new is None: raise EditError('element %d is not a family type (no FamilySymbol.m_familyId): change_type refused' % o['type_eid'])
    fam_old = _field64(ed, cur, 'FamilySymbol.m_familyId')
    if fam_old is None or fam_old != fam_new: raise EditError('type %d belongs to another family than the current type %d of element %d: change_type refused (same-family types only)' % (o['type_eid'], cur, o['eid']))
    if cur == o['type_eid']: raise EditError('element %d already has type %d' % (o['eid'], cur))
    ed.set_field(o['eid'], 'FamilyInstance.m_masterSymbolId', o['type_eid'], fmt='<Q')


def _move_datum(ed, o):
    """Level / Grid move: the datum's position is Plane.m_origin (stored twice in the element record; DatumPlane.m_freeEnd/m_bubbleEnd are constant defaults, measured on Autodesk HVAC 2024).
    Level: only dz (a level is a horizontal plane; in-plane shifts are refused). Grid: only the component along the plane normal (shifting a grid along its own line changes extents that are not rewritten here: refused)."""
    import struct, math
    g = ed.g; log = g.e.trace(o['eid'])[3]
    org = [l for l in log if l[1] == 'Plane.m_origin' and l[3] - l[2] == 24]
    xv = [l for l in log if l[1] == 'Plane.m_xVec' and l[3] - l[2] == 24]; yv = [l for l in log if l[1] == 'Plane.m_yVec' and l[3] - l[2] == 24]
    if len(org) != 2 or len(xv) != 2 or len(yv) != 2: raise NotImplementedError('class datum: unexpected Plane layout (%d origins)' % len(org))
    x = struct.unpack_from('<3d', g.bj, xv[0][2]); y = struct.unpack_from('<3d', g.bj, yv[0][2])
    n = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]); L = math.sqrt(sum(c * c for c in n))
    if not 0.999 < L < 1.001: raise NotImplementedError('class datum: plane axes are not orthonormal')
    n = tuple(c / L for c in n); d = (o['dx'], o['dy'], o['dz']); dn = sum(d[i] * n[i] for i in range(3))
    inplane = math.sqrt(max(0.0, sum(c * c for c in d) - dn * dn))
    if inplane > 1e-9: raise EditError('element %d: only a move perpendicular to the %s (along its normal) is supported; the in-plane part (%.6g) was refused' % (o['eid'], 'level plane' if o['cls'] == 'Level' else 'grid plane', inplane))
    sh = tuple(dn * c for c in n); edits = []
    for l in org:
        v = struct.unpack_from('<3d', g.bj, l[2]); edits.append((l[2], 24, struct.pack('<3d', *(v[i] + sh[i] for i in range(3)))))
    ed._rec_edit(o['eid'], edits)


def _rvtedit_pass(a, b, ops):
    import rvtedit
    ed = rvtedit.Edit(a); deleted = []
    for o in ops:
        try:
            if o['op'] == 'delete': deleted += _delete(ed, o['eid'])
            elif o['op'] == 'move':
                try: ed.move(o['eid'], o['dx'], o['dy'], o['dz'])
                except NotImplementedError as ne:
                    if ('class Level' in str(ne) or 'class Grid' in str(ne)) and os.environ.get('RVTBALLET_ENABLE_LEVELMOVE') == '1': _move_datum(ed, dict(o, cls='Level' if 'class Level' in str(ne) else 'Grid')); continue      # view annotations (TextNote): origin in TextElement.m_orig, 2D in the view plane
                    if 'class TextNote' not in str(ne): raise
                    if o['dz']: raise NotImplementedError('annotation move needs dz = 0')
                    if os.environ.get('RVTBALLET_ENABLE_LEADERNOTEMOVE') != '1':      # active leader (Leader.m_type != 0): whether Revit moves the leader end with the note is not yet confirmed in the VM (opt-in until it is)
                        import struct
                        ld = {l[1]: l for l in ed.g.e.trace(o['eid'])[3]}
                        if 'Leader.m_type' in ld and struct.unpack_from('<i', ed.g.bj, ld['Leader.m_type'][2])[0] != 0: raise NotImplementedError('text note with an active leader: moving the leader end is not verified in Revit yet, so the move is refused (opt-in RVTBALLET_ENABLE_LEADERNOTEMOVE=1)')
                    ed.move_annotation(o['eid'], o['dx'], o['dy'])
            elif o['op'] == 'rotate': ed.rotate(o['eid'], o['deg'])
            elif o['op'] == 'change_type': _change_type(ed, o)
            elif o['op'] == 'set_num': _set_num_by_pid(ed, o)
            elif o['op'] == 'set_string' and o.get('kind') == 'AString': _set_string_by_pid(ed, o)
            elif o['field'] == 'ParamValueAString.m_value': ed.set_string(o['eid'], o['match'], o['value'])
            else:
                if o['field'] in ('DatumPlane.m_text', 'DBView.m_viewName', 'SymbolInfo.m_name'): _check_element_name(o['value'])
                if o['field'] in ('DatumPlane.m_text', 'DBView.m_viewName'): _check_datum_name_unique(a, o)
                ed._str_edit(o['eid'], o['field'], o['value'], o['match'])
        except (IndexError, KeyError, StopIteration, AssertionError, struct_error()) as e:
            hint = ' (the record layout of this kind of element, e.g. a group member, is not handled by the edit backend)' if o['op'] in ('move', 'rotate') else ''
            if o['op'] == 'rotate' and isinstance(e, KeyError): hint = ' (rotate is only supported for placed family instances such as columns, doors and furniture; walls, floors and annotations cannot be rotated here)'
            raise EditError('element %d: %s could not be applied (%s)%s; nothing was changed' % (o['eid'], o.get('field') or o['op'] + (' parameter %s' % o['pid'] if o.get('pid') is not None else ''), type(e).__name__, hint))
        except RuntimeError as e:        # e.g. rvtedit: 'element N lives in Partitions/X but this save edits Partitions/Y' (one partition per save)
            raise EditError('edit refused by the edit backend: %s' % e)
    try: ed.save(b)
    except RuntimeError as e: raise EditError('save refused by the edit backend: %s' % e)
    try:      # the members this writer actually rewrote, declared to the gate (savegate dirty_members rule): a flip in any OTHER member of the partition is then refused
        for pn, pt in ed.g.e.parts.items(): _DIRTY.d.setdefault(pn, set()).update(k for k, m in enumerate(pt.mem) if m.get('dirty'))
    except Exception: _DIRTY.d = None      # unknown: declare nothing (the gate's other checks still apply)
    return deleted


def _value_entry(log, kind, id_entry):
    """the value entry that belongs to a parameter-id entry, by exact byte contiguity. Layout (measured on 2024 records): String and Int values come directly AFTER their id, Double values directly BEFORE it
    (a value can also be contiguous with the NEXT parameter's id, so the order of the two checks matters per kind)"""
    vname = 'ParamValue%s.m_value' % kind
    after = next((x for x in log if x[1] == vname and x[2] == id_entry[3]), None); before = next((x for x in log if x[1] == vname and x[3] == id_entry[2]), None)
    return (before or after) if kind == 'Double' else (after or before)


def _set_num_by_pid(ed, o):
    """overwrite the stored Double/Int value of ONE parameter (exact entry, not rvtedit.set_num's 'previous value within 8 entries', which edits the neighbouring Int for every Int but the first)"""
    import struct
    pid = _resolve_pid(ed, o); log = ed.g.e.trace(o['eid'])[3]
    for l in log:
        if l[1] == 'ParamValue%s.m_paramId' % o['kind'] and _eid_val(l[4]) == pid:
            vn = _value_entry(log, o['kind'], l)
            if vn is None: break
            nb = struct.pack('<d' if o['kind'] == 'Double' else '<i', o['value'])
            if len(nb) != vn[3] - vn[2]: raise AssertionError('value size mismatch')
            ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('param %d (%s) not stored on %d' % (pid, o['kind'], o['eid']))


NAME_FORBIDDEN = set('\\:{}[]|;<>?`~')


def _check_element_name(v):
    """Revit refuses empty names and names with any of \\ : { } [ ] | ; < > ? ` ~ for levels, grids, views and types; the writer used to save them (c5x-rvtread)"""
    bad = sorted(set(v) & NAME_FORBIDDEN)
    if not v.strip(): raise EditError('a name must not be empty; nothing was changed')
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in v): raise EditError('a name must not contain control characters (newline, tab, ...); nothing was changed')
    if len(v) > 255: raise EditError('a name is limited to 255 characters here (conservative; Revit limits are not VM-verified above that); nothing was changed')
    if bad: raise EditError('name contains characters Revit does not allow in names (%s); nothing was changed' % ' '.join(bad))


def _check_datum_name_unique(src, o):
    """Revit does not allow two Levels, two Grids or two views of one kind with the same name (case-insensitive): refuse a rename onto a sibling's name (c5x-rvtread; the writer used to save it). Views: same class (DBViewPlan, DBViewSection, ...), conservative"""
    import rvt_entities
    fld, pre = ('m_viewName', ('DBView',)) if o['field'] == 'DBView.m_viewName' else ('m_text', ('Level', 'Grid'))
    r = rvt_entities.extract(src, slim=lambda c: c.startswith(pre))
    mine = [k for k in r['recs'] if k[0] == o['eid'] and k[1].startswith(pre)]
    if not mine: return
    new = o['value'].strip().casefold()
    for k, v in r['recs'].items():
        if k[1] == mine[0][1] and k[0] != o['eid'] and str(v.get('fields', {}).get(fld, '')).strip().casefold() == new:
            raise EditError('a %s named %r already exists (element %d): Revit does not allow duplicate names; nothing was changed' % (k[1], o['value'], k[0]))


def _set_string_by_pid(ed, o):
    """overwrite the string value that belongs to ONE parameter id (exact log entry), not 'the first value with this text'"""
    import struct
    pid = _resolve_pid(ed, o); log = ed.g.e.trace(o['eid'])[3]
    for k, l in enumerate(log):
        if l[1] == 'ParamValueAString.m_paramId' and _eid_val(l[4]) == pid:
            # the value entry is the one whose bytes are CONTIGUOUS with this id entry (directly after, else directly before): never 'the nearest value' (that picked the neighbouring parameter)
            vn = _value_entry(log, 'AString', l)
            if vn is None: break
            nb = struct.pack('<I', len(o['value'])) + o['value'].encode('utf-16le'); ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('string parameter %d not stored on %d' % (pid, o['eid']))


UNIQUE_CLASS = __import__('re').compile(r'(Tracker|Settings?(Elem|Element)?|Table|Manager|Navigator|Library|Cache|Lock)$|^AllProject|^ProjectInfo|^Units')      # singleton-style classes; evidence: AllProjectRevisions delete -> Revit repair dialog (c7x-rvtmatrix, 2024 VM)


DELETE_VM_VERIFIED = {'CategoryElem', 'BasePoint', 'BrowserOrganization', 'SWall', 'ColorFillSchema', 'Floor', 'CompoundCeilingType', 'DBViewPlan', 'AutoJoinTracker', 'AssemblyCodeTable', 'Viewport', 'DimensionStyle', 'RoomElem'}      # Revit 2024 VM, single-element delete on the cols2 scene: opens with no repair prompt (SWall: only Revit's own 'Room is not in a properly enclosed region' warning, the true consequence of removing a bounding wall) (c7x-rvtmatrix); RoomElem clean in VM too; extend only with a VM verdict


def _delete(ed, eid):
    """delete with what Revit's Delete removes: class-specific paths of rvtedit (floor / view / sheet), else owned_set; returns every deleted id (they all go in the manifest)"""
    cls = ed.g.e.trace(eid)[2]['class']
    if os.environ.get('RVTBALLET_DELETE_ANY') != '1' and cls not in DELETE_VM_VERIFIED:
        raise EditError('element %d is a %s: delete is only enabled for classes whose output was opened in Revit without a repair prompt (%s); other classes are refused (override for experiments: RVTBALLET_DELETE_ANY=1)' % (eid, cls, ', '.join(sorted(DELETE_VM_VERIFIED))))
    if cls not in DELETE_VM_VERIFIED and UNIQUE_CLASS.search(cls): raise EditError('element %d is a %s: a project-wide settings / tracker / table element that Revit expects to exist exactly once (deleting AllProjectRevisions made Revit show "Repair Missing Unique Elements"); not deleted' % (eid, cls))
    if cls == 'Floor': return list(ed.delete_floor(eid))
    if cls.startswith('DBView') and cls not in ('DBViewType',): return list(ed.delete_view(eid))
    if cls == 'ViewSheet': return list(ed.delete_sheet(eid) or [eid])
    ids = ed.owned_set(eid); ed.delete(*ids); return list(ids)


def struct_error():
    import struct
    return struct.error
