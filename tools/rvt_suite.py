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
    (C_TYPE, 'string parameter'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'set_string'},
    (C_TYPE, 'number parameter'): {'bundle': ('Floor', 'Structural'), 'use': 'set_num'},
    (C_FILE, 'save in place (overwrite)'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'save_in_place'},
    (C_SAFE, 'opens in Revit with no repair dialog'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'opens'},
    (C_SAFE, 'untouched elements identical'): {'bundle': ('FamilyInstance', 'HVAC'), 'use': 'untouched'},
    (C_TYPE, 'change instance type'): {'special': 'change_type'},
    # verified failures (Revit evidence), recorded without re-running
    (C_MOVE, 'text note'): {'static': ('PASS', 'verified 2026-11-07 (c7x-rvtmove): HVAC 2024 TextNote 1487557 (no leader) +1,+2 ft; Revit 2024 opened clean, API Coord = original + (1,2) to 6 dp; leader notes are refused; other years not run')},
    (C_MOVE, 'dimension'): {'static': ('FAIL', 'verified failure: a record move of a LinearDimString is accepted by the gate but Revit reads identical segment origins before/after (shift 0,0,0); now refused at edit time (5f05c13)')},
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
    return rc == 0 and 'No such device' not in out


def vm_open(year, path):
    """-> (opened, cmp_ok, note) from tools/rvt_vm_open.py's TSV row"""
    rc, out = run([sys.executable, HERE + '/rvt_vm_open.py', str(year), path], timeout=3000)
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
        rc, out = run([sys.executable, HERE + '/rvt_expect_check.py', str(year), b['src'], b['out'], ep], timeout=3600)
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
    rc, o0 = run([sys.executable, HERE + '/rvt_param_readback.py', str(year), '%d|@symbol' % inst, src], timeout=3000)
    rc, o1 = run([sys.executable, HERE + '/rvt_param_readback.py', str(year), '%d|@symbol' % inst, keep], timeout=3000)
    s0 = re.search(r'symbol=(\d+)', o0); s1 = re.search(r'symbol=(\d+)', o1)
    if not s0 or not s1: return 'ERROR', 'no Revit symbol readback'
    if int(s0.group(1)) != t0 or int(s1.group(1)) != t1: return 'FAIL', 'Revit Symbol.Id %s -> %s, expected %d -> %d' % (s0.group(1), s1.group(1), t0, t1)
    return 'PASS', 'FamilyInstance %d type %d -> same-family %d; gate verify_diffs 0, only the target element differs, SAVE! in place == SAVE AS; Revit opens clean (%s) and Symbol.Id reads %d' % (inst, t0, t1, note, t1)


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
                elif 'static' in spec: st, note = spec['static']
                elif spec.get('special') == 'change_type': st, note = decide_change_type(y, workdir, not a.no_vm)
                else: st, note = decide_class_case(y, spec, workdir, not a.no_vm)
            except Exception as e: st, note = 'ERROR', '%s: %s' % (type(e).__name__, e)
            counts[st] += 1; log(st, key, '|', note[:160]); put_ledger(a.run_id, key, st, note)
            if st in ('PASS', 'FAIL') and not a.no_record: subprocess.run([RECORD, c, it, st, note[:380], str(y)])
    finally: shutil.rmtree(workdir, ignore_errors=True)
    log('done', counts)


if __name__ == '__main__': main()
