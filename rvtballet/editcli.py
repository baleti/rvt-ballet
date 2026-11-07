"""rvt-ballet info FILE | edit FILE OPS... (-o OUT | --in-place) | edit --list-ops

Preliminary command-line editing. It drives the SAME code the viewer's //commands and SAVE! use (rvtballet.server routes in-process, savegate gate, element-level
verify), so a CLI edit is accepted or refused exactly like the same edit in the page. Default writes a NEW file; the input is never modified unless --in-place is
given AND the SAVE! policy is switched on (RVTBALLET_ALLOW_OVERWRITE=1). No shell tricks and no fixed paths: works wherever the viewer works."""
import os, sys, json, argparse, asyncio, tempfile, shutil

# What passes today. Source of truth is the Revit-VM ledger (~/demo-state/rvt-edit/ledger.jsonl, dashboard); this table is the user-facing summary. Honest limits.
# status: supported = PASS in the Revit VM (open without repair dialog + API readback) | experimental = needs an opt-in environment variable | refused = the gate refuses it
OPS = [
    ('set-string EID PARAM VALUE', 'supported', '2024 2025 2026', 'string parameter (Mark, Comments, ...) on an element that already stores it; value <= 4096 chars, BMP only'),
    ('set-num EID PARAM VALUE', 'supported', '2024 2025 2026', 'number parameter that is already stored as a Double (Revit internal units, feet for lengths)'),
    ('move EID DX DY DZ', 'supported', '2024 2025 2026', 'FamilyInstance (|d| <= 50000 ft). Level and Grid moves: experimental (RVTBALLET_ENABLE_LEVELMOVE=1); TextNote moves (with leader) follow the note in Revit, on by default. Wall move: refused by the gate (member span rule), under review'),
    ('rotate EID DEG', 'supported', '2024 2025 2026', 'placed FamilyInstance only (columns, doors, furniture); |deg| <= 360'),
    ('delete EID', 'experimental', '2024', 'needs RVTBALLET_ENABLE_DELETE=1 (and RVTBALLET_DELETE_ANY=1 outside the verified classes); FamilyInstance verified on HVAC 2024 only'),
    ('change-type EID TYPE_EID', 'experimental', '2024', 'same-family FamilySymbol only; needs RVTBALLET_ENABLE_CHANGETYPE=1; Revit verdict pending'),
    ('add (wall, floor, level, ...)', 'refused', '-', 'not available on arbitrary projects yet (the write lab adds to its seed project; generalisation in progress)'),
]
YEARS = 'Revit years: 2024, 2025 and 2026 can be saved (2025: move, rotate, Mark judged in Revit 2025). 2020-2023 files are refused (12-byte record layout not enabled). Worksharing, groups and design options are refused.'


def _ledger_counts():
    p = os.path.expanduser('~/demo-state/rvt-edit/ledger.jsonl')
    try: rows = [json.loads(l) for l in open(p) if l.strip()]
    except OSError: return None
    return sum(1 for r in rows if r.get('result') == 'PASS'), sum(1 for r in rows if r.get('result') == 'FAIL')


def list_ops(out=print):
    out('rvt-ballet edit operations (status = evidence level, see the dashboard for the Revit-VM ledger):')
    for name, st, yrs, note in OPS: out('  %-30s %-13s years: %-10s %s' % (name, st, yrs, note))
    out(YEARS)
    c = _ledger_counts()
    if c: out('ledger: %d PASS rows, %d FAIL rows (~/demo-state/rvt-edit/ledger.jsonl)' % c)
    out('Default writes a NEW file (-o OUT). The original is never modified. --in-place needs RVTBALLET_ALLOW_OVERWRITE=1 (SAVE! policy) and goes through the savegate with backup and verify.')


class _Op(argparse.Action):
    def __init__(self, option_strings, dest, **kw): self.kind = kw.pop('kind'); super().__init__(option_strings, dest, **kw)
    def __call__(self, parser, ns, values, option_string=None): ns.ops.append((self.kind, values))


def _parser():
    ap = argparse.ArgumentParser(prog='rvt-ballet edit', description='preliminary editing of a Revit file; see --list-ops')
    ap.add_argument('file', nargs='?'); ap.add_argument('-o', '--output', help='write the edited copy here (must not exist; never the input)')
    ap.add_argument('--in-place', action='store_true', help='overwrite the input through the savegate (needs RVTBALLET_ALLOW_OVERWRITE=1)')
    ap.add_argument('--overwrite-output', action='store_true', help='allow -o to replace an existing OUT (never the input)')
    ap.add_argument('--list-ops', action='store_true'); ap.set_defaults(ops=[])
    ap.add_argument('--set-string', nargs=3, metavar=('EID', 'PARAM', 'VALUE'), action=_Op, kind='set_string')
    ap.add_argument('--set-num', nargs=3, metavar=('EID', 'PARAM', 'VALUE'), action=_Op, kind='set_num')
    ap.add_argument('--move', nargs=4, metavar=('EID', 'DX', 'DY', 'DZ'), action=_Op, kind='move')
    ap.add_argument('--rotate', nargs=2, metavar=('EID', 'DEG'), action=_Op, kind='rotate')
    ap.add_argument('--delete', nargs=1, metavar='EID', action=_Op, kind='delete')
    ap.add_argument('--set-type-num', nargs=3, metavar=('TYPE_EID', 'PARAM', 'VALUE'), action=_Op, kind='set_type_num')
    ap.add_argument('--change-type', nargs=2, metavar=('EID', 'TYPE_EID'), action=_Op, kind='change_type')
    return ap


def build_op(kind, v):
    """CLI words -> viewer edit op dict; ValueError with a one-line reason on bad numbers"""
    def i(x, what):
        try: return int(x)
        except ValueError: raise ValueError('%s must be an integer, got %r' % (what, x))
    def f(x, what):
        try: return float(x)
        except ValueError: raise ValueError('%s must be a number, got %r' % (what, x))
    if kind == 'set_string': return {'op': 'set_string', 'eid': i(v[0], 'EID'), 'param': v[1], 'value': v[2]}
    if kind == 'set_num': return {'op': 'set_num', 'eid': i(v[0], 'EID'), 'param': v[1], 'value': f(v[2], 'VALUE')}
    if kind == 'move': return {'op': 'move', 'eid': i(v[0], 'EID'), 'dx': f(v[1], 'DX'), 'dy': f(v[2], 'DY'), 'dz': f(v[3], 'DZ')}
    if kind == 'rotate': return {'op': 'rotate', 'eid': i(v[0], 'EID'), 'deg': f(v[1], 'DEG')}
    if kind == 'delete': return {'op': 'delete', 'eid': i(v[0], 'EID')}
    if kind == 'set_type_num': return {'op': 'set_type_num', 'eid': i(v[0], 'TYPE_EID'), 'param': v[1], 'value': f(v[2], 'VALUE')}
    if kind == 'change_type': return {'op': 'change_type', 'eid': i(v[0], 'EID'), 'type_eid': i(v[1], 'TYPE_EID')}
    raise ValueError('unknown op ' + kind)


def _status_of(kind):
    key = kind.replace('_', '-')
    for name, st, yrs, note in OPS:
        if name.split()[0] == key: return st
    return 'unknown'


def check_paths(src, out, in_place, overwrite_output):
    """-> reason string when the combination is refused, else None. The input is never a valid -o target."""
    if in_place and out: return '--in-place and -o are mutually exclusive'
    if not in_place and not out: return 'give -o OUT.rvt (writes a new file) or --in-place'
    if in_place:
        if os.environ.get('RVTBALLET_ALLOW_OVERWRITE') != '1': return 'in-place saving is off (SAVE! policy): set RVTBALLET_ALLOW_OVERWRITE=1 to enable it; use -o OUT.rvt to write a copy instead. The file was not touched'
        return None
    try: same = os.path.exists(out) and os.path.samefile(src, out)
    except OSError: same = False
    if same or os.path.realpath(out) == os.path.realpath(src): return 'OUT is the input file: refusing to overwrite the original (use --in-place, with the SAVE! policy on)'
    if os.path.exists(out) and not overwrite_output: return 'OUT already exists: %s (use --overwrite-output to replace it)' % out
    return None


async def _run(src, ops, out, in_place, say):
    os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    from . import server
    tmp = tempfile.mkdtemp(prefix='rvtballet-cli-')
    try:
        models = server.Models(); models.m['m'] = {'dir': tmp, 'name': os.path.basename(src), 'src': src}
        async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
            si = await (await c.get('/api/m/m/saveinfo')).json()
            if not si.get('available'): say('saving is not available here (savegate not installed)'); return 3
            if si.get('workshared'): say('refused: workshared (central/local) models cannot be saved; the file was not touched'); return 3
            if not si.get('open'): say('refused: Revit %s files cannot be saved by this build (supported: 2024, 2025, 2026); the file was not touched' % si.get('version')); return 3
            for kind, v in ops:
                op = build_op(kind, v); st = _status_of(kind)
                r = await c.post('/api/m/m/edit', json=op); j = await r.json()
                if r.status != 200: say('refused [%s]: %s %s: %s' % (st, kind, ' '.join(v), j.get('error', j))); return 3
                say('accepted [%s]: %s %s' % (st, kind, ' '.join(v)))
            if in_place: r = await c.post('/api/m/m/save', json={})
            else: r = await c.post('/api/m/m/saveas', json={'dest': out, 'overwrite': True} if os.path.exists(out) else {'dest': out})
            j = await r.json()
            if r.status != 200: say('refused by the gate (%s): %s\nthe %s was not changed' % (j.get('code'), j.get('error'), 'original' if in_place else 'input')); return 3
            say('%s: %s (%s bytes, verified: %s unexpected differences)' % ('saved in place' if in_place else 'wrote', j.get('dest', out), j.get('size'), (j.get('verify') or {}).get('n_unexpected')))
            if j.get('backup'): say('backup: ' + j['backup'])
            for w in j.get('warnings') or []: say('warning: ' + str(w))
            return 0
    finally: shutil.rmtree(tmp, ignore_errors=True)


def edit_main(argv, say=print):
    ap = _parser(); a = ap.parse_args(argv)
    if a.list_ops: list_ops(say); return 0
    if not a.file: ap.error('FILE is required (or use --list-ops)')
    if not a.ops: say('nothing to do: give at least one operation (see --list-ops)'); return 2
    from . import cli
    bad = cli.check_input(a.file)
    if bad: say('rvt-ballet: ' + bad); return 2
    why = check_paths(a.file, a.output, a.in_place, a.overwrite_output)
    if why: say('rvt-ballet: ' + why); return 2
    try:
        for kind, v in a.ops: build_op(kind, v)
    except ValueError as ex: say('rvt-ballet: ' + str(ex)); return 2
    return asyncio.run(_run(os.path.abspath(a.file), a.ops, os.path.abspath(a.output) if a.output else None, a.in_place, say))


def info_main(argv, say=print):
    ap = argparse.ArgumentParser(prog='rvt-ballet info'); ap.add_argument('file'); ap.add_argument('--json', action='store_true'); a = ap.parse_args(argv)
    from . import cli
    bad = cli.check_input(a.file)
    if bad: say('rvt-ballet: ' + bad); return 2
    src = os.path.abspath(a.file)
    async def go():
        from aiohttp.test_utils import TestClient, TestServer
        from . import server
        tmp = tempfile.mkdtemp(prefix='rvtballet-cli-')
        try:
            models = server.Models(); models.m['m'] = {'dir': tmp, 'name': os.path.basename(src), 'src': src}
            async with TestClient(TestServer(server.make_app(models))) as c: return await (await c.get('/api/m/m/saveinfo')).json()
        finally: shutil.rmtree(tmp, ignore_errors=True)
    si = asyncio.run(go())
    if a.json: say(json.dumps(si, indent=1, default=str)); return 0
    say('%s: %.1f MB' % (os.path.basename(src), os.path.getsize(src) / 1e6))
    for k in ('version', 'worksharing', 'workshared', 'open', 'gate_open', 'allow_overwrite', 'error'):
        if k in si: say('  %-16s %s' % (k, si[k]))
    say('  editable        %s' % ('yes (preliminary: rvt-ballet edit --list-ops)' if si.get('open') and not si.get('workshared') else 'no'))
    return 0
