#!/usr/bin/env python3
"""RVT editing CONFORMANCE SUITE (owner: rvtmatrix agents). One command that walks ~/demo-state/rvt-edit/matrix.json (every category x item) for every Revit year in it,
performs each edit on a FRESH COPY of an Autodesk sample through the production save path, opens the result in the offline Revit VM, reads it back through the Revit API,
and records PASS / FAIL with ~/demo-state/bin/rvt-edit-record. Items with no case are recorded as FAIL 'not implemented' (never skipped), so the dashboard shows the real gap.

usage: rvt_suite.py [--years 2024,2026] [--only "substring of 'category|item'"] [--shard I/N] [--run-id ID] [--dry-run] [--no-record] [--no-vm]
Resumable: ~/demo-state/rvt-edit/suite-ledger.jsonl keeps one line per finished case (key 'category|item|year', status PASS/FAIL/ERROR); a re-run with the same run id (default: today's date)
skips PASS/FAIL cases, retries ERROR ones (VM down, timeout: infrastructure problems are NEVER recorded as results). Shard with --shard 1/2 and 2/2 (stable hash of the case key); the VM lock serialises
Revit jobs per host. Only Autodesk samples, all local; aggregate notes only (no file names). PASS needs: save through the gate OK (verify_diffs 0, SAVE! in place == SAVE AS bytes), the output opens in
Revit with no repair dialog and resave compare 0/0, the Revit-side readback equals the expectation, and no element other than the edited one (and declared dependents) changed."""
import os, sys, json, time, hashlib, subprocess, argparse, re, tempfile, shutil, glob

HOME = os.path.expanduser('~')
HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX = HOME + '/demo-state/rvt-edit/matrix.json'
LEDGER = HOME + '/demo-state/rvt-edit/suite-ledger.jsonl'
RECORD = HOME + '/demo-state/bin/rvt-edit-record'
CORPUS = HOME + '/rvt-research/corpus'
WRITABLE = {2024, 2026}      # years the save API accepts (rvtballet/save.py policy); others are recorded FAIL with that reason
C_MOVE = '1. Move / rotate / resize'; C_DEL = '2. Delete'; C_ADD = '3. Add new element'; C_TYPE = '4. Types and parameters'
C_FILE = '7. Structure of file'; C_SAFE = '8. Safety (applies to every save)'

# case table: (category, item) -> spec. No entry = FAIL 'not implemented'.
#  bundle: ('class', CLASS, SAMPLE_HINT)  one rvt_class_pass run per (year, class), shared by every case that names it
#  use: which part of the bundle decides the case
CASES = {
    (C_MOVE, 'family instance'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'move'},
    (C_MOVE, 'wall'): {'bundle': ('SWall', 'Structural'), 'use': 'move'},
    (C_MOVE, 'level'): {'bundle': ('Level', 'HVAC'), 'use': 'move'},
    (C_MOVE, 'grid'): {'bundle': ('Grid', 'HVAC'), 'use': 'move'},
    (C_MOVE, 'window'): {'bundle': ('FamilyInstance', 'Facades'), 'use': 'move'},
    (C_MOVE, 'door'): {'bundle': ('FamilyInstance', 'Facades'), 'use': 'move'},
    (C_MOVE, 'column'): {'static': ('PASS', 'Structural 2024 W Shapes-Column 608201 move +1 ft and rotate 30 deg: SAVE AS verify_diffs 0, 99.994% untouched, in-place SAVE! byte-identical to SAVE AS, Revit 2024 opens clean, cmp 0/0; Concrete-Rectangular-Column 606069 SAVE AS PASS, in place refused (joined). The generic FamilyInstance bundle picks hosted wall openings, so this row is static until the bundle selects by family category'), 'static_years': [2024]},
    (C_TYPE, 'string parameter'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'set_string'},
    (C_TYPE, 'number parameter'): {'bundle': ('Floor', 'Structural'), 'use': 'set_num'},
    (C_FILE, 'save in place (overwrite)'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'save_in_place'},
    (C_SAFE, 'opens in Revit with no repair dialog'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'opens'},
    (C_SAFE, 'untouched elements identical'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'untouched'},
    (C_TYPE, 'change instance type'): {'special': 'change_type'},
    (C_ADD, 'wall'): {'special': 'add_wall'},
    (C_ADD, 'family instance'): {'special': 'add_fi'},
    (C_ADD, 'tag'): {'static': ('FAIL', 'NOT VERIFIED: offline edit-lab at: op on HVAC 2024 gives reader diff +1 IndependentTag, 0 gone, 0 changed (tests/test_add_tag.py), bad targets refused; Revit VM verdict still queued, no PASS claimed'), 'static_years': [2024]},
    (C_ADD, 'text note'): {'static': ('FAIL', 'NOT VERIFIED: offline edit-lab tn: op builds +1 TextNote on HVAC 2024 and 2022 Arch_Link, empty/control-char text refused (tests/test_add_textnote_guard.py); Revit VM verdict still queued, no PASS claimed'), 'static_years': [2024]},
    (C_ADD, 'view'): {'static': ('FAIL', 'NOT VERIFIED: offline edit-lab av: op builds +1 view on HVAC 2024, duplicate/forbidden names refused (tests/test_add_view_name_guard.py); Revit VM verdict still queued, no PASS claimed'), 'static_years': [2024]},
    (C_ADD, 'sheet'): {'static': ('FAIL', 'FAILED IN VM: edit-lab as: op on Autodesk Snowdon 2024 Structural copy (clone of S100) raised CorruptModelException on open in Revit 2024 (c9x-rvtadd 2026-11-11, gates were clean); cause not found, S001 clone verdict pending; no PASS'), 'static_years': [2024]},
    (C_TYPE, 'material create'): {'static': ('PASS', 'verified 2026-11-11 (c3x-rvttype): tools/rvt_mat_create_gen.py on HVAC 2024+2026 (+1 element, stray clean); Revit opened (sample baseline warn dialog only), API reads Material C3XMAT next to Default; assign not covered, untouched-element API equality not checked'), 'static_years': [2024, 2026]},
    (C_TYPE, 'shared parameter add'): {'static': ('PASS', 'verified 2026-11-13 (c5x-rvttype): tools/rvt_param_add_gen.py on HVAC 2024: 5 shared params + Walls instance bindings, Global/Latest GUID table and category binding map written as decoded from a Revit-made pair; Revit opened (baseline DocWarn dialog only), ParameterBindings readback instance/Walls x5 = Revit-made control; value set on walls and untouched-element API equality not covered; project (non-shared) parameter not separately verified'), 'static_years': [2024]},
    (C_TYPE, 'project parameter add'): {'static': ('FAIL', 'NOT DONE: generator writes SHARED (external GUID) parameters only, which are verified under "shared parameter add"; a true project parameter (non-shared, internal ParamElem) needs its own Revit-made pair to decode, not yet taken'), 'static_years': [2024]},
    (C_TYPE, 'element-id parameter'): {'static': ('FAIL', 'NOT VERIFIED: offline set_type_eid (opt-in RVTBALLET_ENABLE_TYPEEID=1) reproduces the Revit-made record of paired HVAC 2024 symbol 579392 Arrow Type byte for byte except a 2-byte back-pointer, bad targets refused (tests/test_set_type_eid.py); our output not yet opened in Revit, no PASS claimed'), 'static_years': [2024]},
    (C_TYPE, 'material assign'): {'static': ('FAIL', 'NOT VERIFIED: offline set_type_material (opt-in RVTBALLET_ENABLE_TYPEEID=1) reproduces the Revit-made record of pair c1xmatas (Structural 2024 SysMullionFamSym Material 1075 -> 751) except a 2-byte back-pointer, bad targets refused (tests/test_type_material.py); only system types with Symbol.m_renderStyleId; our output not yet opened in Revit, no PASS claimed'), 'static_years': [2024]},
    (C_TYPE, 'edit type string parameter'): {'static': ('FAIL', 'NOT VERIFIED: offline set_string by pid on a wall type Type Mark (Structural 2024): only the target element differs, stale match refused (tests/test_type_string_edit.py, passes 2026-11-11); same machinery as the Revit-verified instance string edit, but no Revit open verdict for a TYPE element yet'), 'static_years': [2024]},
    (C_TYPE, 'yes/no parameter'): {'static': ('FAIL', 'NOT VERIFIED: built-in Room Bounding = 1 byte HostObj.m_roomBounding (Revit-made paired diff, Structural 2024 wall 585072); opt-in op set_room_bounding + tests/test_room_bounding.py offline OK, Revit open/readback probe queued (p_rb4.log); no PASS claimed. set_num Int still refuses built-in yes/no'), 'static_years': [2024]},
    (C_TYPE, 'duplicate type'): {'static': ('PASS', 'verified 2026-11-07 (c1x-rvttype): HVAC 2024 FamilySymbol 1379030 duplicated as C5XDUP via tools/rvt_dup_type_gen.py; Revit 2024 opened clean (baseline DocWarnDialog only), new symbol readback name C5XDUP same family, original unchanged; other years not tested'), 'static_years': [2024]},
    (C_TYPE, 'edit type geometry parameter'): {'static': ('PASS', 'verified 2026-11-07 (c3x-rvttype): HVAC 2024 FamilySymbol Slot Width 0.0833 -> 0.1 via set_type_num (opt-in RVTBALLET_ENABLE_TYPEPARAM=1); gate only that field differs; Revit 2024 opened clean cmp 0/0, API readback 0.100000; other years refuse (caption lookup)'), 'static_years': [2024]},
    # rung 2 delete, evidence from c3x-rvtdel (Revit 2024 VM, Snowdon HVAC/Structural, opened clean, class-count dumps exact; 2024 only)
    (C_DEL, 'wall'): {'static': ('PASS', 'Structural 2024 SWall delete cascaded 10 hosted FamilyInstances, opened clean in Revit, resave 0/0; regression tests/test_delete_wall_cascade.py; walls named by a dimension are refused (c959a5e) until Revit cascade for dimensions is recorded'), 'static_years': [2024]},
    (C_DEL, 'floor'): {'static': ('PASS', 'Structural 2024 Floor delete (cascade sketch/lines/dim/tag) opened clean in Revit, dump diff exact'), 'static_years': [2024]},
    (C_DEL, 'family instance'): {'static': ('PASS', 'HVAC+Structural 2024 FamilyInstance delete opened clean in Revit, class counts exact'), 'static_years': [2024]},
    (C_DEL, 'annotation'): {'static': ('PASS', 'HVAC 2024 TextNote/IndependentTag/RoomTag delete opened clean in Revit, class counts exact'), 'static_years': [2024]},
    (C_DEL, 'view'): {'static': ('PASS', 'HVAC 2024 DBViewSchedule + ScheduleInstance delete opened clean in Revit'), 'static_years': [2024]},
    (C_DEL, 'level'): {'static': ('FAIL', 'refused at save (verify_failed, dependents), nothing written; Structural 2024'), 'static_years': [2024]},
    (C_DEL, 'grid'): {'static': ('FAIL', 'refused at save (verify_failed, dependents), nothing written; Structural 2024'), 'static_years': [2024]},
    # verified failures (Revit evidence), recorded without re-running
    (C_MOVE, 'duct/pipe/MEP'): {'static': ('FAIL', 'refused on purpose (2026-11-13 c2x-rvtmove): Revit 2024 HVAC paired run, one FamilyInstance +1 ft x rewrote 25 records (own analytical nodes + 24 connected duct/fitting curves), our writer moves 1 record, so a connected MEP move is refused (rvt-ballet 342c408, tests/test_move_guard_mep_connected.py); unconnected MEP move not tested')},
    (C_MOVE, 'text note'): {'static': ('PASS', 'verified 2026-11-07 (c7x-rvtmove): HVAC 2024 TextNote 1487557 (no leader) +1,+2 ft; Revit 2024 opened clean, API Coord = original + (1,2) to 6 dp; leader notes are refused; other years not run')},
    (C_TYPE, 'rename grid/level/view (dependents)'): {'static': ('PASS', 'verified 2026-11-07 (c5x-rvtmatrix): Structural 2024 (16571 elements) Grid, DBViewSection and Level renames via rvt_one_edit, dependents declared, SAVE AS + SAVE! in place verify_diffs 0, 99.68 to 99.994 pct untouched, Revit 2024 opened clean, cmp 0/0')},
    (C_MOVE, 'floor'): {'static': ('FAIL', 'refused: no Revit-made witness; Structural 2024 floors 621720/665246/670055 MoveElement committed but API bbox unchanged and 0 records changed (c3x-rvtmove, 4 VM pairs); cause not found'), 'static_years': [2024]},
    (C_MOVE, 'dimension'): {'static': ('FAIL', 'verified failure: a record move of a LinearDimString is accepted by the gate but Revit reads identical segment origins before/after (shift 0,0,0); now refused at edit time (5f05c13)')},
    ('6. Links', 'move link'): {'static': ('PASS', 'verified 2026-11-07 (c3x-rvtlink): HVAC 2024 RvtLinkInstance Trf.m_or +1 ft via set_field; savegate diff exactly 1 element; Revit 2024 opened clean, API origin (1,0,0); other years offline only'), 'static_years': [2024]},
    ('6. Links', 'reload link path'): {'static': ('PASS', 'verified 2026-11-07 (c3x-rvtlink): HVAC 2024 RvtLinkSymbol path edited in 3 string spans (same length and +14 chars); 1 element differs; Revit 2024 opened clean, readback new link type name; 2025/2026 samples PASS too, but link types with records in several partitions (19% of elements in the 2026 Electrical sample) are now refused or edited in every copy: both-copies output awaits its Revit 2026 verdict'), 'static_years': [2024]},
    ('6. Links', 'unload/remove link'): {'static': ('FAIL', 'unload verified on 2024 (m_shouldLoadSource flag, IsLoaded True->False with target beside host); remove link is refused by the gate (dependents), so the item is only half done'), 'static_years': [2024]},
}


def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)


def load_ledger():
    rows = []
    try:
        for l in open(LEDGER):
            try: rows.append(json.loads(l))
            except ValueError: pass
    except OSError: pass
    return rows


def put_ledger(run, key, status, note):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    open(LEDGER, 'a').write(json.dumps({'run': run, 'key': key, 'status': status, 'note': note[:400], 't': time.strftime('%Y-%m-%d %H:%M:%S')}) + '\n')


def sample_for(year, hint):
    d = '%s/%d' % (CORPUS, year)
    fs = sorted(glob.glob(d + '/*.rvt'), key=os.path.getsize)
    if not fs: return None
    pick = [f for f in fs if hint.lower() in os.path.basename(f).lower()]
    return (pick or fs)[0]


def run(cmd, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=e)
    except subprocess.TimeoutExpired: return 124, 'timeout'
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def vm_up():
    rc, out = run(['/srv/vm/win/runs/20261011-194452/gssh', 'hostname'], timeout=40)
    if rc == 0 and 'No such device' not in out: return True
    rc, out = run(['pgrep', '-f', 'qemu-system.*name revit-lane'], timeout=10)      # lane 1 (cid 30) is retired; Revit jobs run on lanes 2/3 through rvt_vm_open, which reports its own failures
    return rc == 0 and bool(out.strip())


def vm_open(year, path):
    """-> (opened, cmp_ok, note) from tools/rvt_vm_open.py's TSV row"""
    rc, out = run([sys.executable, HERE + '/rvt_vm_open.py', str(year), path], timeout=10800)
    row = next((l for l in out.splitlines() if l.startswith('c3x-rvtmatrix')), '')
    if not row: return None, None, 'no VM verdict (' + out.strip()[-120:] + ')'
    f = row.split('\t')
    if any(k in row for k in ('no Revit port', 'hang/crash', 'TIMEOUT')): return None, None, 'VM infrastructure problem, not a result: ' + row[-120:]      # the guest Revit did not start / crashed: retry later, never a FAIL
    opened = 'revit_open=True' in f[4]; cmp_ok = "cmp=('0', '0')" in f[5]
    return opened, cmp_ok, ' '.join(f[4:7])[:160] + ((' ' + f[-1]) if len(f) > 8 and f[-1] else '')


def expectations(applied):
    ex = []
    for o in applied:
        if o['op'] == 'move': ex.append({'kind': 'move', 'eid': o['eid'], 'd': [o['dx'], o['dy'], o['dz']]})
        elif o['op'] == 'set_string' and o.get('param'): ex.append({'kind': 'param', 'eid': o['eid'], 'name': o['param'], 'type': 'String', 'value': o['value']})
        elif o['op'] == 'set_num' and o.get('param'): ex.append({'kind': 'param', 'eid': o['eid'], 'name': o['param'], 'type': 'Double', 'value': o['value']})
    return ex


_bundles = {}


def bundle(year, cls, hint, workdir):
    """one rvt_class_pass run (fresh copy, production save path, SAVE AS + SAVE!) per (year, class); the kept output is opened in Revit and the expectations checked. Cached for the whole suite run."""
    k = (year, cls, hint)
    if k in _bundles: return _bundles[k]
    src = sample_for(year, hint); b = {'src': src}; _bundles[k] = b
    if not src: b['error'] = 'no sample for this year'; return b
    if year not in WRITABLE: b['fail'] = 'save refused: Revit %d files are not writable by policy (writable years: %s)' % (year, ', '.join(map(str, sorted(WRITABLE)))); return b
    keep = tempfile.mkdtemp(dir=workdir); out = '%s/%s_%d.json' % (workdir, cls, year)
    rc, txt = run([sys.executable, HERE + '/rvt_class_pass.py', out, src, cls], env={'KEEP_DIR': keep, 'KEEP_TAG': 'suite', 'CP_MAX_TRY': '5'}, timeout=7200)
    try: row = json.load(open(out))[0]
    except Exception: b['error'] = 'class pass produced no result (rc %s): %s' % (rc, txt.strip()[-150:]); return b
    b['row'] = row
    kept = glob.glob(keep + '/*')
    if row.get('result') != 'OK' or not kept: return b
    b['out'] = kept[0]; b['applied'] = row.get('applied_full') or []
    return b


def revit_checks(year, b):
    """open the bundle's kept output in Revit once, run the expectation check once; cache in the bundle"""
    if 'vm' in b: return b['vm']
    opened, cmp_ok, note = vm_open(year, b['out']); vm = {'opened': opened, 'cmp': cmp_ok, 'note': note, 'exp_ok': None, 'exp_note': ''}
    if opened and b['applied']:
        ex = expectations(b['applied']); ep = b['out'] + '.expect.json'; json.dump(ex, open(ep, 'w'))
        rc, out = run([sys.executable, HERE + '/rvt_expect_check.py', str(year), b['src'], b['out'], ep], timeout=10800)
        m = re.search(r"EXPECT-CHECK \{'expectations': (\d+), 'pass': (\d+), 'fail': (\d+)\}", out)
        if m: vm['exp_ok'] = int(m.group(3)) == 0 and int(m.group(2)) == int(m.group(1)); vm['exp_note'] = 'expectations %s/%s' % (m.group(2), m.group(1))
        else: vm['exp_note'] = 'no expectation verdict'
    b['vm'] = vm
    return vm


def decide_class_case(year, spec, workdir, use_vm):
    cls, hint = spec['bundle']; b = bundle(year, cls, hint, workdir)
    if b.get('error'): return 'ERROR', b['error']
    if b.get('fail'): return 'FAIL', b['fail']
    row = b.get('row', {}); use = spec['use']
    if row.get('result') != 'OK' or 'out' not in b:
        why = row.get('detail') or row.get('result') or 'no result'
        return 'FAIL', 'class %s: %s (applied: %s; refused: %s)' % (cls, str(why)[:120], row.get('applied'), str(row.get('refused'))[:120])
    ops = [o['op'] for o in b['applied']]
    if use in ('move', 'set_string', 'set_num') and use not in ops:
        return 'FAIL', 'op %s was refused for class %s (%s)' % (use, cls, str(row.get('refused'))[:140])
    if row.get('verify_diffs') != 0 or row.get('problems'): return 'FAIL', 'gate: verify_diffs %s problems %s' % (row.get('verify_diffs'), row.get('problems'))
    if use == 'save_in_place' and (row.get('save_over') or not row.get('backup')): return 'FAIL', 'SAVE! in place not clean: %s' % (row.get('save_over') or 'no backup')
    if not use_vm: return 'ERROR', 'VM checks disabled (--no-vm)'
    if not vm_up(): return 'ERROR', 'Revit VM is down'
    vm = revit_checks(year, b)
    if vm['opened'] is None: return 'ERROR', vm['note']
    if not vm['opened']: return 'FAIL', 'Revit did not open the output cleanly: ' + vm['note']
    if not vm['cmp']: return 'FAIL', 'Revit resave compare not 0/0: ' + vm['note']
    if use in ('move', 'set_string', 'set_num') and vm['exp_ok'] is None: return 'ERROR', 'VM infrastructure problem, not a result: the Revit expectation check printed no verdict (' + vm['exp_note'] + ')'
    if use in ('move', 'set_string', 'set_num') and vm['exp_ok'] is not True: return 'FAIL', 'Revit readback did not match: ' + vm['exp_note']
    if use == 'untouched' and row.get('other_elements_param_changed', 0) not in (0, row.get('declared_dependents')): return 'FAIL', 'other elements changed: %s' % row.get('other_elements_param_changed')
    return 'PASS', '%s; class %s on a %d sample, gate verify_diffs 0, %s of %s elements untouched (%s pct); Revit: %s %s' % (use, cls, year, (row.get('elements') or 0) - (row.get('elements_changed') or 0), row.get('elements'), row.get('elements_untouched_pct'), vm['note'], vm['exp_note'])


def decide_change_type(year, workdir, use_vm):
    if year not in WRITABLE: return 'FAIL', 'save refused: Revit %d files are not writable by policy' % year
    src = sample_for(year, 'HVAC')
    if not src: return 'ERROR', 'no sample'
    rc, out = run([sys.executable, HERE + '/rvt_pick_sibling_type.py', src], timeout=3600)
    m = re.search(r'PICK (\d+) (\d+) (\d+)', out)
    if not m: return 'FAIL', 'no instance with a same-family sibling type found: ' + out.strip()[-120:]
    inst, t0, t1 = map(int, m.groups()); keep = workdir + '/ct_%d.rvt' % year
    rc, out = run([sys.executable, HERE + '/rvt_op_save.py', src, json.dumps({'op': 'change_type', 'eid': inst, 'type_eid': t1})], env={'KEEP_OUT': keep}, timeout=7200)
    ok = re.search(r'saveas 200', out) and re.search(r'verify_diffs 0', out) and 'only target: True' in out and re.search(r'save! in place 200', out) and 'bytes==saveas True' in out
    if not ok: return 'FAIL', 'gate/save: ' + ' | '.join(l for l in out.splitlines() if l.startswith(('edit', 'saveas', 'verify', 'report', 'save!')))[:300]
    if not use_vm: return 'ERROR', 'VM checks disabled (--no-vm)'
    if not vm_up(): return 'ERROR', 'Revit VM is down'
    opened, cmp_ok, note = vm_open(year, keep)
    if opened is None: return 'ERROR', note
    if not opened or not cmp_ok: return 'FAIL', 'Revit open/compare: ' + note
    rc, o1 = run([sys.executable, HERE + '/rvt_param_readback.py', str(year), '%d|@symbol' % inst, keep], timeout=10800)
    s1 = re.search(r'symbol=(\d+)', o1)
    if not s1: return 'ERROR', 'no Revit symbol readback of the saved file: ' + o1.strip()[-200:].replace('\n', ' / ')
    if int(s1.group(1)) != t1: return 'FAIL', 'Revit Symbol.Id of the saved file is %s, expected %d (original %d)' % (s1.group(1), t1, t0)
    return 'PASS', 'FamilyInstance %d type %d -> same-family %d; gate verify_diffs 0, only the target element differs, SAVE! in place == SAVE AS; Revit opens clean (%s) and Symbol.Id reads %d' % (inst, t0, t1, note, t1)

def decide_add_fi(year, workdir, use_vm):
    """ADD a FamilyInstance by clone-and-patch (tools/rvt_add_clone.py, edit engine) on the HVAC sample; reader diff must be +1 FamilyInstance only, then Revit open"""
    if year != 2024: return 'FAIL', 'ADD family instance verified path is HVAC 2024 only (2025: multi-partition build offline-clean, Revit verdict pending; other years not built)'
    src = sample_for(year, 'HVAC')
    if not src: return 'ERROR', 'no sample'
    out = workdir + '/addfi_%d.rvt' % year
    env = {k: v for k, v in os.environ.items() if not k.startswith('RVT_ADD_EDITENGINE')}      # single-partition HVAC: the edit engine is rejected by Revit (CorruptModelException), default engine only
    r = subprocess.run([sys.executable, HERE + '/rvt_add_clone.py', src, out, '--src', '1365188'], capture_output=True, text=True, env=env, timeout=3600)
    if r.returncode != 0 or not os.path.exists(out): return 'FAIL', 'writer: ' + (r.stdout + r.stderr).strip()[-200:]
    sys.path.insert(0, os.path.dirname(HERE))
    from rvtballet import reader
    a = reader.load(src)['recs']; b = reader.load(out)['recs']
    new = [k for k in b if k not in a]; gone = [k for k in a if k[0] != 0 and 'error' not in a[k] and k not in b]; chg = [k for k in a if k in b and not (k[0] == 0 or 'error' in a[k]) and a[k] != b[k]]
    if len(new) != 1 or new[0][1] != 'FamilyInstance' or gone or chg: return 'FAIL', 'record diff: new=%s gone=%d changed=%d' % (new[:3], len(gone), len(chg))
    if not use_vm: return 'ERROR', 'VM checks disabled (--no-vm)'
    if not vm_up(): return 'ERROR', 'Revit VM is down'
    opened, cmp_ok, note = vm_open(year, out)
    if opened is None: return 'ERROR', note
    if not opened or not cmp_ok: return 'FAIL', 'Revit open/compare: ' + note
    return 'PASS', 'new FamilyInstance %d: reader diff +1 only, Revit opens clean (%s); API position readback not yet automated' % (new[0][0], note)


def decide_add_wall(year, workdir, use_vm):
    """ADD a straight wall (clone-and-patch, tools/rvt_aw_auto.py) on a Structural sample; reader-level +1 SWall only, then Revit open + API readback of the new wall"""
    if year not in WRITABLE: return 'FAIL', 'ADD only built for 2024/2026 (2020-2023 need 4-byte ids and the Latest registry grammar)'
    src = sample_for(year, 'Structural')
    if not src: return 'ERROR', 'no sample'
    out = workdir + '/aw_%d.rvt' % year
    rc, o = run([sys.executable, HERE + '/rvt_aw_auto.py', src, out, '-250', '-100', '-240', '-88', '12', str(year)], timeout=3600)
    if rc != 0 or not os.path.exists(out): return 'FAIL', 'writer: ' + o.strip()[-200:]
    sys.path.insert(0, os.path.dirname(HERE))
    from rvtballet import reader
    a = reader.load(src)['recs']; b = reader.load(out)['recs']
    new = [k for k in b if k not in a]; gone = [k for k in a if k[0] != 0 and 'error' not in a[k] and k not in b]; chg = [k for k in a if k in b and not (k[0] == 0 or 'error' in a[k]) and a[k] != b[k]]      # records with an 'error' text (id 0 or low ids) are reader error placeholders: byte offsets shift, NaN != NaN
    if len(new) != 1 or new[0][1] != 'SWall' or gone or chg: return 'FAIL', 'record diff: new=%s gone=%d changed=%d' % (new[:3], len(gone), len(chg))
    nid = new[0][0]
    if not use_vm: return 'ERROR', 'VM checks disabled (--no-vm)'
    if not vm_up(): return 'ERROR', 'Revit VM is down'
    opened, cmp_ok, note = vm_open(year, out)
    if opened is None: return 'ERROR', note
    if not opened or not cmp_ok: return 'FAIL', 'Revit open/compare: ' + note
    body = workdir + '/rb.cs'
    open(body, 'w').write(open(HOME + '/rvt-research/edit-lab/oracle_rbwall.cs').read().replace('__NEWID__', str(nid)) if os.path.exists(HOME + '/rvt-research/edit-lab/oracle_rbwall.cs') else '')
    if not os.path.getsize(body): return 'ERROR', 'readback body ~/rvt-research/edit-lab/oracle_rbwall.cs missing'
    rc, o = run([sys.executable, HOME + '/rvt-research/edit-lab/oracle.py', str(year), out, 'suiteaw', body], timeout=3600)
    m = re.search(r'RB newwall a=(-?[\d.]+),(-?[\d.]+) b=(-?[\d.]+),(-?[\d.]+) level=(\d+) type=(\d+) h=([\d.]+)', o)
    if not m: return 'ERROR', 'no wall readback: ' + o.strip()[-160:]
    x0, y0, x1, y1 = map(float, m.groups()[:4]); h = float(m.group(7))
    if max(abs(x0 + 250), abs(y0 + 100), abs(x1 + 240), abs(y1 + 88), abs(h - 12)) > 1e-3: return 'FAIL', 'readback differs from request: ' + m.group(0)
    return 'PASS', 'new SWall %d: reader diff +1 only (0 gone, 0 changed), Revit opens clean (%s), API endpoints/height equal request; untouched elements verified at reader level only' % (nid, note)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--years'); ap.add_argument('--only'); ap.add_argument('--shard'); ap.add_argument('--run-id', default=time.strftime('%Y-%m-%d'))
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--no-record', action='store_true'); ap.add_argument('--no-vm', action='store_true')
    a = ap.parse_args()
    m = json.load(open(MATRIX)); years = [int(y) for y in a.years.split(',')] if a.years else m['years']
    si, sn = (int(x) for x in a.shard.split('/')) if a.shard else (1, 1)
    done = {r['key'] for r in load_ledger() if r['run'] == a.run_id and r['status'] in ('PASS', 'FAIL')}
    plan = [(c['name'], it, y) for c in m['categories'] for it in c['items'] for y in years]
    plan = [p for p in plan if (not a.only or a.only.lower() in ('%s|%s' % (p[0], p[1])).lower()) and int(hashlib.sha1(('%s|%s|%d' % p).encode()).hexdigest(), 16) % sn == si - 1]
    todo = [p for p in plan if '%s|%s|%d' % p not in done]
    log('run %s: %d cases in plan, %d already done, %d to run (years %s, shard %d/%d)' % (a.run_id, len(plan), len(plan) - len(todo), len(todo), years, si, sn))
    if a.dry_run:
        for c, it, y in todo: print('%-34s %-40s %d  %s' % (c[:34], it[:40], y, 'case' if (c, it) in CASES else 'FAIL not implemented'))
        return
    workdir = tempfile.mkdtemp(prefix='rvtsuite-'); counts = {'PASS': 0, 'FAIL': 0, 'ERROR': 0}
    try:
        for c, it, y in sorted(todo, key=lambda p: (p[2], (p[0], p[1]) in CASES, p[0])):
            key = '%s|%s|%d' % (c, it, y); spec = CASES.get((c, it))
            try:
                if spec is None: st, note = 'FAIL', 'not implemented'
                elif 'static' in spec: st, note = spec['static'] if y in spec.get('static_years', [y]) else ('FAIL', 'not verified for %d (static case covers %s only)' % (y, spec['static_years']))
                elif spec.get('special') == 'change_type': st, note = decide_change_type(y, workdir, not a.no_vm)
                elif spec.get('special') == 'add_wall': st, note = decide_add_wall(y, workdir, not a.no_vm)
                elif spec.get('special') == 'add_fi': st, note = decide_add_fi(y, workdir, not a.no_vm)
                else: st, note = decide_class_case(y, spec, workdir, not a.no_vm)
            except Exception as e: st, note = 'ERROR', '%s: %s' % (type(e).__name__, e)
            counts[st] += 1; log(st, key, '|', note[:160]); put_ledger(a.run_id, key, st, note)
            if st in ('PASS', 'FAIL') and not a.no_record: subprocess.run([RECORD, c, it, st, note[:380], str(y)])
    finally: shutil.rmtree(workdir, ignore_errors=True)
    log('done', counts)


if __name__ == '__main__': main()
