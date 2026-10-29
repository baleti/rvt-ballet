"""Edit model for SAVE: a per-model list of ops replayed on the loaded bytes with the write-lab Editor (rvt-research/write-lab/wledit.py).
Ops: {'op': 'set_string', 'eid': int, 'field': 'ParamValueAString.m_value' (default), 'value': str, 'match': optional old text}.
The manifest handed to savegate declares exactly the edited elements ('el:<id>' keys), so verify fails if anything else changed."""
import os, sys, tempfile

WL = os.path.expanduser(os.environ.get('RVTBALLET_WRITELAB', '~/rvt-research/write-lab'))
DEFAULT_FIELD = 'ParamValueAString.m_value'
FIELDS = ('ParamValueAString.m_value', 'DatumPlane.m_text', 'DBView.m_viewName', 'SymbolInfo.m_name')   # string fields validated in write-lab (e3/e4)


class EditError(Exception): pass


def validate_op(op):
    if not isinstance(op, dict) or op.get('op') != 'set_string': raise EditError('unsupported edit op (supported: set_string)')
    if not isinstance(op.get('eid'), int) or isinstance(op.get('eid'), bool): raise EditError('eid (element id) must be an integer')
    if not isinstance(op.get('value'), str): raise EditError('value must be a string')
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
    def manifest(self): return {'modified': sorted({'el:%d' % o['eid'] for o in self.ops})}


def apply(buf, ops):
    """replay ops on bytes -> new bytes (the source bytes are never modified)"""
    if not ops: return buf
    if WL not in sys.path: sys.path.insert(0, WL)
    import wledit
    d = tempfile.mkdtemp(prefix='rvtballet-edit-'); a = os.path.join(d, 'in.rvt'); b = os.path.join(d, 'out.rvt')
    try:
        with open(a, 'wb') as f: f.write(buf)
        ed = wledit.Editor(a)
        for o in ops:
            try: ed.set_string(o['eid'], o['field'], o['value'], match=o['match'])
            except (IndexError, KeyError, StopIteration, struct_error()) as e:
                raise EditError('element %d has no %s to edit (%s)' % (o['eid'], o['field'], type(e).__name__))
        ed.save(b)
        with open(b, 'rb') as f: return f.read()
    finally:
        for p in (a, b):
            try: os.remove(p)
            except OSError: pass
        try: os.rmdir(d)
        except OSError: pass


def struct_error():
    import struct
    return struct.error
