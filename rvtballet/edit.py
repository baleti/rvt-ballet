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
    import rvt_params
    ids = [int(k) for k, v in rvt_params.PNAMES.items() if v == name]
    if not ids: raise EditError('unknown parameter name %r (not in the reader\'s built-in table)' % name)
    return ids          # several categories can share a name: the one stored on the element is chosen when the op is applied


def validate_op(op):
    if not isinstance(op, dict) or op.get('op') not in ('set_string', 'set_num', 'delete', 'move'): raise EditError('unsupported edit op (supported: set_string, set_num, delete, move)')
    if not isinstance(op.get('eid'), int) or isinstance(op.get('eid'), bool): raise EditError('eid (element id) must be an integer')
    if op['op'] == 'move':
        if BACKEND() != 'rvtedit': raise EditError('move needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        d = [op.get(k, 0.0) for k in ('dx', 'dy', 'dz')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e6 for v in d): raise EditError('dx, dy, dz must be finite numbers (Revit internal units = feet), |v| <= 1e6')
        if not any(d): raise EditError('move by zero')
        return {'op': 'move', 'eid': op['eid'], 'dx': float(d[0]), 'dy': float(d[1]), 'dz': float(d[2])}
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
        pid = op.get('pid'); cands = None
        if pid is None: cands = _pid_for(op.get('param') or '')
        elif not isinstance(pid, int) or isinstance(pid, bool): raise EditError('pid must be an integer')
        if BACKEND() != 'rvtedit': raise EditError('set_num needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        return {'op': 'set_num', 'eid': op['eid'], 'pid': pid, 'pids': cands, 'param': op.get('param'), 'value': float(v) if kind == 'Double' else int(v), 'kind': kind}
    if not isinstance(op.get('value'), str): raise EditError('value must be a string')
    if op.get('param') is not None or op.get('pid') is not None:       # address the parameter by NAME/ID instead of by old text (several string parameters can hold the same text)
        if BACKEND() != 'rvtedit': raise EditError('editing a parameter by name or id needs the rvtedit backend (RVTBALLET_EDIT_BACKEND=rvtedit)')
        pid = op.get('pid'); cands = None
        if pid is None: cands = _pid_for(op.get('param') or '')
        elif not isinstance(pid, int) or isinstance(pid, bool): raise EditError('pid must be an integer')
        if '\0' in op['value'] or len(op['value']) > 4096: raise EditError('value must not contain NUL and must be at most 4096 characters')
        return {'op': 'set_string', 'eid': op['eid'], 'field': 'ParamValueAString.m_value', 'value': op['value'], 'match': None, 'pid': pid, 'pids': cands, 'param': op.get('param'), 'kind': 'AString'}
    if '\0' in op['value'] or len(op['value']) > 4096: raise EditError('value must not contain NUL and must be at most 4096 characters')
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
        m = {'modified': sorted({'el:%d' % o['eid'] for o in self.ops if o['op'] != 'delete'})}
        if deleted: m['deleted'] = sorted('el:%d' % i for i in deleted)
        return m


def apply(buf, ops): return apply_full(buf, ops)[0]


def apply_full(buf, ops):
    """replay ops on bytes -> new bytes (the source bytes are never modified). Backend: env RVTBALLET_EDIT_BACKEND = wledit (default) | rvtedit"""
    if not ops: return buf, []
    d = tempfile.mkdtemp(prefix='rvtballet-edit-'); a = os.path.join(d, 'in.rvt'); b = os.path.join(d, 'out.rvt')
    try:
        with open(a, 'wb') as f: f.write(buf)
        deleted = (_apply_rvtedit if BACKEND() == 'rvtedit' else _apply_wledit)(a, b, ops) or []
        with open(b, 'rb') as f: return f.read(), deleted
    finally:
        for p in (a, b):
            try: os.remove(p)
            except OSError: pass
        try: os.rmdir(d)
        except OSError: pass


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


def _resolve_pid(ed, o):
    """explicit pid, or the single candidate id for the parameter NAME that is actually stored (as the given kind) on this element"""
    if o.get('pid') is not None: return o['pid']
    log = ed.g.e.trace(o['eid'])[3]; stored = set()
    for l in log:
        if l[1] == 'ParamValue%s.m_paramId' % o['kind']:
            try: v = int(str(l[4])[4:-1]); stored.add(v - (1 << 64) if v >= (1 << 63) else v)
            except ValueError: pass
    hit = [c for c in o['pids'] if c in stored]
    if len(hit) != 1: raise EditError('parameter %r: %d candidate ids stored as %s on element %d (need exactly 1; give pid)' % (o.get('param'), len(hit), o['kind'], o['eid']))
    return hit[0]


def _apply_rvtedit(a, b, ops):
    """rvtedit works on ONE partition per save (env PART): in multi-partition files the ops are grouped by the partition each element lives in and applied as sequential passes (pass n reads the output of pass n-1), exactly as rvtedit's own command line does"""
    for p in (EL, WL, os.path.expanduser('~/rvt-research')):
        if p not in sys.path: sys.path.insert(0, p)
    os.environ.setdefault('RVT_GEOM', '1')
    import rvtedit, shutil
    saved_part = os.environ.get('PART')
    try:
        os.environ.pop('PART', None); probe = rvtedit.Edit(a); multi = len(probe.g.e.m.parts) > 1; groups = {}
        for o in ops:
            pn = None
            if multi:
                try: pn = (getattr(probe, 'latest_partition', lambda e: None)(o['eid']) or probe.g.e.trace(o['eid'])[0])
                except Exception: pn = None
            groups.setdefault(pn, []).append(o)
        del probe
        deleted = []; cur = a; tmps = []
        for n, (pn, grp) in enumerate(groups.items()):
            last = n == len(groups) - 1; out = b if last else os.path.join(os.path.dirname(b), 'pass%d.rvt' % n)
            if pn: os.environ['PART'] = str(pn)
            else: os.environ.pop('PART', None)
            deleted += _rvtedit_pass(cur, out, grp)
            if not last: tmps.append(out)
            cur = out
        for t in tmps:
            try: os.remove(t)
            except OSError: pass
        return deleted
    finally:
        if saved_part is None: os.environ.pop('PART', None)
        else: os.environ['PART'] = saved_part


def _rvtedit_pass(a, b, ops):
    import rvtedit
    ed = rvtedit.Edit(a); deleted = []
    for o in ops:
        try:
            if o['op'] == 'delete': deleted += _delete(ed, o['eid'])
            elif o['op'] == 'move': ed.move(o['eid'], o['dx'], o['dy'], o['dz'])
            elif o['op'] == 'set_num': _set_num_by_pid(ed, o)
            elif o['op'] == 'set_string' and o.get('kind') == 'AString': _set_string_by_pid(ed, o)
            elif o['field'] == 'ParamValueAString.m_value': ed.set_string(o['eid'], o['match'] if o['match'] is not None else None, o['value'])
            else: ed._str_edit(o['eid'], o['field'], o['value'], o['match'])
        except (IndexError, KeyError, StopIteration, AssertionError, struct_error()) as e:
            raise EditError('element %d: %s could not be applied (%s)' % (o['eid'], o.get('field') or o['op'] + (' parameter %s' % o['pid'] if o.get('pid') is not None else ''), type(e).__name__))
        except RuntimeError as e:        # e.g. rvtedit: 'element N lives in Partitions/X but this save edits Partitions/Y' (one partition per save)
            raise EditError('edit refused by the edit backend: %s' % e)
    try: ed.save(b)
    except RuntimeError as e: raise EditError('save refused by the edit backend: %s' % e)
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
    pid = _resolve_pid(ed, o); want = 'EID(%d)' % (pid & ((1 << 64) - 1)); log = ed.g.e.trace(o['eid'])[3]
    for l in log:
        if l[1] == 'ParamValue%s.m_paramId' % o['kind'] and l[4] == want:
            vn = _value_entry(log, o['kind'], l)
            if vn is None: break
            nb = struct.pack('<d' if o['kind'] == 'Double' else '<i', o['value'])
            if len(nb) != vn[3] - vn[2]: raise AssertionError('value size mismatch')
            ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('param %d (%s) not stored on %d' % (pid, o['kind'], o['eid']))


def _set_string_by_pid(ed, o):
    """overwrite the string value that belongs to ONE parameter id (exact log entry), not 'the first value with this text'"""
    import struct
    pid = _resolve_pid(ed, o); want = 'EID(%d)' % (pid & ((1 << 64) - 1)); log = ed.g.e.trace(o['eid'])[3]
    for k, l in enumerate(log):
        if l[1] == 'ParamValueAString.m_paramId' and l[4] == want:
            # the value entry is the one whose bytes are CONTIGUOUS with this id entry (directly after, else directly before): never 'the nearest value' (that picked the neighbouring parameter)
            vn = _value_entry(log, 'AString', l)
            if vn is None: break
            nb = struct.pack('<I', len(o['value'])) + o['value'].encode('utf-16le'); ed._rec_edit(o['eid'], [(vn[2], vn[3] - vn[2], nb)]); return
    raise KeyError('string parameter %d not stored on %d' % (pid, o['eid']))


def _delete(ed, eid):
    """delete with what Revit's Delete removes: class-specific paths of rvtedit (floor / view / sheet), else owned_set; returns every deleted id (they all go in the manifest)"""
    cls = ed.g.e.trace(eid)[2]['class']
    if cls == 'Floor': return list(ed.delete_floor(eid))
    if cls.startswith('DBView') and cls not in ('DBViewType',): return list(ed.delete_view(eid))
    if cls == 'ViewSheet': return list(ed.delete_sheet(eid) or [eid])
    ids = ed.owned_set(eid); ed.delete(*ids); return list(ids)


def struct_error():
    import struct
    return struct.error
