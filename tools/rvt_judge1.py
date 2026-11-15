#!/usr/bin/env python3
"""rvt_judge1.py: the Revit-VM judgement of rvt_judge.py in ONE lane lock and ONE Revit open per file (c4x-rvteditopus, 2026-11-15).
  single:  rvt_judge1.py YEAR ORIG.rvt OUT.rvt EXPECT.json ALLOWED_IDS [WORKDIR]      (same arguments and verdict line as rvt_judge.py)
  batch:   rvt_judge1.py --batch CASES.tsv [WORKDIR]    one line per case: YEAR<TAB>ORIG<TAB>OUT<TAB>EXPECT.json<TAB>ALLOWED_IDS[<TAB>NAME]
Why: rvt_judge.py runs rvt_vm_open (lock, 2 opens), rvt_expect_check (up to 4 sessions, each its own lock) and rvt_elemhash_readback (lock, 2 opens):
4 to 6 lane-lock waits (median wait 935 s, p90 5030 s on 2026-11-14/15) and 6+ Revit opens per verdict, re-judging the same unedited original every time.
Here every file is opened ONCE by tools/rvt_judge1.cs, which performs the same checks with the same formulas (verify2 audit open + SaveAs/reopen COMPARE + BBOXNULL,
elemhash of every element and type, location/frame readback, parameter readback); the control (ORIG) result is cached by year + sha256 + guest script + ids,
so a batch of N edits of one sample costs 1 lock and N+1 opens (N when the control is cached).
Verdict rules = rvt_judge.py, plus two stricter ones: a DIALOG id or an Error/DocumentCorruption FAILURE that the output shows and the control does not is a FAIL.
Exit 0 PASS, 1 FAIL, 2 oracle produced no usable output (no verdict), 3 infrastructure (no Revit port). Autodesk samples / synthetic only; ids stay local."""
import sys, os, re, json, hashlib, time
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); sys.path.insert(0, H)
CS = os.path.join(H, 'rvt_judge1.cs')
CACHE = os.path.expanduser(os.environ.get('RVT_JUDGE1_CACHE', '~/.cache/rvt_judge1'))
RS = chr(30)

def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def ids_for(exp):
    loc = sorted({str(e['eid']) for e in exp if e['kind'] in ('move', 'rotate', 'absent')}, key=int)
    par = sorted({'%d|%s' % (e['eid'], e['name']) for e in exp if e['kind'] == 'param'})
    return loc, par

def parse(txt):
    """j1 text -> dict: ok flags, dialogs, failures, eh {id: hash}, loc text, par text"""
    import rvt_expect_check as X
    r = {'raw_ok': 'RESULT ok' in txt, 'dialogs': sorted(set(re.findall(r'^DIALOG (\S+)', txt, re.M))),
         'failures': sorted(set(l for l in re.findall(r'^FAILURE (.*)$', txt, re.M) if not l.startswith('Warning'))),
         'cmp': re.search(r'COMPARE only_original=(\d+) only_resaved=(\d+)', txt), 'bboxnull': re.search(r'BBOXNULL (\d+)', txt),
         'err': (re.search(r'RESULT fail (.*)', txt) or [None, ''])[1] if 'RESULT fail' in txt else '',
         't_open': (re.search(r'T_OPEN (\d+)', txt) or [None, None])[1], 't_total': (re.search(r'T_TOTAL (\d+)', txt) or [None, None])[1]}
    r['cmp'] = r['cmp'].groups() if r['cmp'] else None; r['bboxnull'] = int(r['bboxnull'].group(1)) if r['bboxnull'] else None
    r['eh'] = {int(a): b for a, b in re.findall(r'^EH (\d+) ([0-9a-f]{8})', txt, re.M)}
    r['ed'] = {int(a): b for a, b in re.findall(r'^ED (\d+) (.*)$', txt, re.M)}
    r['volatile'] = {int(x) for x in re.findall(r'^VOLATILE (\d+)$', txt, re.M)}
    r['loc'] = X.parse_loc('\n'.join(l for l in txt.splitlines() if l.startswith(('RB ', 'TF '))))
    r['par'] = X.parse_par('\n'.join('RB ' + l[4:] for l in txt.splitlines() if l.startswith('RBP ')))
    r['opened'] = r['raw_ok'] and r['cmp'] == ('0', '0') and r['bboxnull'] is not None and 'CorruptModel' not in txt and not any('Repair' in d for d in r['dialogs'])
    return r

def verdict(c, o, exp, allowed, emit=print):
    """c, o = parse() of control and output. Returns (code, why): 0 PASS, 1 FAIL, 2 no usable oracle output."""
    import rvt_expect_check as X
    if not c['raw_ok'] or not c['eh']: return 2, 'control did not produce a dump (%s): no verdict on the output' % c['err'][:120]
    if not c['opened']: return 2, 'control itself does not open clean (cmp %s bboxnull %s dialogs %s): sample not usable as a judge base' % (c['cmp'], c['bboxnull'], c['dialogs'])
    if not o['opened']: return 1, 'output open: result_ok=%s cmp=%s bboxnull=%s dialogs=%s err=%s' % (o['raw_ok'], o['cmp'], o['bboxnull'], o['dialogs'], o['err'][:160])
    if o['bboxnull'] != c['bboxnull']: return 1, 'curve elements with a null bounding box: control %s, output %s' % (c['bboxnull'], o['bboxnull'])      # relative rule: some samples (2020 rme) carry 1510 by themselves
    nd = sorted(set(o['dialogs']) - set(c['dialogs'])); nf = sorted(set(o['failures']) - set(c['failures']))
    if nd: return 1, 'output shows dialogs the control does not: %s' % nd
    if nf: return 1, 'output shows non-warning failures the control does not: %s' % [x[:80] for x in nf[:3]]
    npass, nfail = X.evaluate(exp, {'orig': c, 'out': o}, emit)
    if nfail: return 1, 'readback: %d of %d expectations fail' % (nfail, len(exp))
    a, b = c['eh'], o['eh']
    diff = {k for k in a.keys() & b.keys() if a[k] != b[k]}; only_a = set(a) - set(b); only_b = set(b) - set(a)
    vol = c.get('volatile') or set()
    if diff & vol - allowed: emit('volatile ids ignored (differ between two Revit opens of the unedited control): %s' % sorted(diff & vol - allowed)[:10])
    bad = diff - allowed - vol; bad_a = only_a - allowed
    emit('elements A %d B %d; differing %d; only-in-A %d; only-in-B %d' % (len(a), len(b), len(diff), len(only_a), len(only_b)))
    emit('differing ids outside the allowed list: %d %s' % (len(bad), sorted(bad)[:10]))
    emit('untouched elements identical in Revit view: %.4f %%' % (100.0 * (len(a.keys() & b.keys()) - len(diff)) / max(1, len(a.keys() & b.keys()))))
    if bad or bad_a or only_b: return 1, 'untouched elements: %d differ outside allowed, %d undeclared missing, %d new' % (len(bad), len(bad_a), len(only_b))
    return 0, 'control and output open clean, readback exact (%d expectations), only the allowed ids differ in Revit (%d elements)' % (npass, len(a))

def guest_run(guest, year, f, loc, par, tag, wd, tries=3, ed=()):
    """one open of f in the guest; returns j1 text or None (infrastructure)"""
    base = tag + os.path.splitext(f)[1]
    cs = open(CS).read().replace('__FILE__', 'C:/wl/' + base).replace('__TAG__', tag).replace('__LOCIDS__', ','.join(loc)).replace('__EDIDS__', ','.join(str(x) for x in ed)).replace('__PARITEMS__', RS.join(par)).replace('__IDT__', 'long' if year >= 2024 else 'int')
    # Revit 2020-2023 API has no ElementId(long) constructor (CS1503 compile error): the id type is per year
    for k in range(tries):
        port = guest.fresh(year)
        if not port: time.sleep(60); continue
        guest.put(f, 'C:/wl/' + base, 900)
        con = guest.run_job(year, port, cs, tag, int(os.environ.get('RVT_JUDGE1_TIMEOUT', '1500')))
        lf = os.path.join(wd, tag + '_j1.txt')
        if os.path.exists(lf): os.remove(lf)
        guest.get('C:/wl/out/%s_j1.txt' % tag, lf, 600)
        try: guest.gssh("Remove-Item -Force -EA 0 'C:/wl/%s','C:/wl/out/%s_j1.txt'" % (base, tag), 60)
        except Exception: pass
        txt = open(lf, errors='replace').read() if os.path.exists(lf) else ''
        if 'RESULT' in txt: return txt
        open(os.path.join(wd, tag + '_console%d.txt' % k), 'w').write(con or '')
        if 'RESULT fail' in (con or ''): return con      # the job ran and failed to open: that IS the observation (the file write may not have happened)
        guest.down(year)      # hang / crash / no output: fresh Revit for the retry
    return None

def judge_batch(cases, wd):
    """cases: [dict(year, orig, out, exp, allowed, name)] -> list of (case, code, why). One lane lock for everything."""
    import guest
    os.makedirs(wd, exist_ok=True); os.makedirs(CAC := CACHE, exist_ok=True); cshash = sha(CS)[:12]
    os.environ.setdefault('RVT_WARM', '1')
    ctl = {}      # (year, orig sha) -> (loc ids, par items) union over the batch
    for c in cases:
        c['osha'] = sha(c['orig']); loc, par = ids_for(c['exp']); k = (c['year'], c['osha'])
        u = ctl.setdefault(k, (set(), set())); u[0].update(loc); u[1].update(par)
    res = []; t_enq = time.time()
    with guest.vmlock() as lk:
        t_acq = time.time(); print('LOCK lane=%s wait=%.0fs' % (os.path.basename(guest.RD.rstrip('/')), t_acq - t_enq), flush=True)
        ctltxt = {}
        for (year, osha), (loc, par) in sorted(ctl.items()):
            loc = sorted(loc, key=int); par = sorted(par)
            key = hashlib.sha256(('%s|%s|%s|%s|%s' % (year, osha, cshash, ','.join(loc), RS.join(par))).encode()).hexdigest()[:24]
            cf = os.path.join(CAC, key + '.txt')
            if os.path.exists(cf): ctltxt[(year, osha)] = open(cf).read(); print('CONTROL cached', year, osha[:8], flush=True); continue
            orig = next(c['orig'] for c in cases if (c['year'], c['osha']) == (year, osha))
            t0 = time.time(); txt = guest_run(guest, year, orig, loc, par, 'j1c%s' % osha[:8], wd)
            print('CONTROL', year, osha[:8], 'sec=%.0f' % (time.time() - t0), 'ok' if txt and 'RESULT ok' in txt else 'NO-OUTPUT', flush=True)
            if txt and parse(txt)['opened'] and os.environ.get('RVT_JUDGE1_NOISE', '1') == '1':      # noise floor: a second open of the same control
                t2 = guest_run(guest, year, orig, loc, par, 'j1n%s' % osha[:8], wd)
                if t2 and parse(t2)['opened']:
                    a, b = parse(txt)['eh'], parse(t2)['eh']; vol = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
                    txt += ''.join('VOLATILE %d\n' % k for k in vol); print('NOISE', year, osha[:8], 'volatile ids', len(vol), flush=True)
            ctltxt[(year, osha)] = txt
            if txt and parse(txt)['opened']: open(cf, 'w').write(txt)      # only a clean control is cached
        for c in cases:
            loc, par = ids_for(c['exp']); ctl_t = ctltxt.get((c['year'], c['osha']))
            if not ctl_t: res.append((c, 3, 'INFRA control produced no output')); continue
            t0 = time.time(); osha = sha(c['out'])
            txt = guest_run(guest, c['year'], c['out'], loc, par, 'j1o%s' % osha[:8], wd)
            if not txt: res.append((c, 3, 'INFRA no Revit output for the output file')); continue
            lines = []; code, why = verdict(parse(ctl_t), parse(txt), c['exp'], c['allowed'], lines.append)
            if code == 1 and why.startswith('untouched') and os.environ.get('RVT_JUDGE1_EXPLAIN', '1') == '1':
                pc, po = parse(ctl_t), parse(txt); ids = sorted((k for k in pc['eh'].keys() & po['eh'].keys() if pc['eh'][k] != po['eh'][k] and k not in c['allowed'] and k not in pc['volatile']))[:20]
                ec = guest_run(guest, c['year'], c['orig'], [], [], 'j1x%s' % c['osha'][:8], wd, ed=ids); eo = guest_run(guest, c['year'], c['out'], [], [], 'j1y%s' % osha[:8], wd, ed=ids)
                if ec and eo:
                    dc, do = parse(ec)['ed'], parse(eo)['ed']
                    for k in ids:
                        a_, b_ = dc.get(k, ''), do.get(k, '')
                        if pc['eh'][k] == parse(ec)['eh'].get(k) and po['eh'][k] == parse(eo)['eh'].get(k):
                            fa = dict(x.split('=', 1) for x in a_.split(';') if '=' in x); fb = dict(x.split('=', 1) for x in b_.split(';') if '=' in x)
                            lines.append('EXPLAIN %d %s: %s' % (k, a_.split('|')[0], '; '.join('%s: %s -> %s' % (n, fa.get(n), fb.get(n)) for n in sorted(set(fa) | set(fb)) if fa.get(n) != fb.get(n))[:600] or 'params equal; tail %r -> %r' % (a_[-160:], b_[-160:])))
                        else: lines.append('EXPLAIN %d unstable: its hash changed between opens (volatile, not a writer change)' % k)
            pr = parse(txt); why += ' [open %s ms, total %s ms, sec %.0f, sha %s]' % (pr['t_open'], pr['t_total'], time.time() - t0, osha[:12])
            open(os.path.join(wd, c['name'] + '.verdict.txt'), 'w').write('\n'.join(lines + [str(code) + ' ' + why]) + '\n')
            print('CASE', c['name'], ['PASS', 'FAIL', 'NOORACLE', 'INFRA'][code], why, flush=True); res.append((c, code, why))
        if os.environ.get('RVT_WARM') == '1':
            for y in sorted({c['year'] for c in cases}): guest.down(y)      # leave the lane clean
        print('LOCK held=%.0fs cases=%d' % (time.time() - t_acq, len(cases)), flush=True)
    return res

def load_case(year, orig, out, expf, allowed, name=None):
    return {'year': int(year), 'orig': os.path.abspath(orig), 'out': os.path.abspath(out), 'exp': json.load(open(expf)) if expf not in ('', '-') else [],
            'allowed': {int(x) for x in allowed.split(',') if x.strip()}, 'name': name or os.path.basename(out).rsplit('.', 1)[0]}

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--batch':
        wd = a[2] if len(a) > 2 else os.path.expanduser('~/c4x-judge1/batch_%d' % time.time())
        cases = [load_case(*l.rstrip('\n').split('\t')) for l in open(a[1]) if l.strip() and not l.startswith('#')]
        r = judge_batch(cases, wd)
        print('BATCH', {k: sum(1 for x in r if x[1] == i) for i, k in enumerate(['PASS', 'FAIL', 'NOORACLE', 'INFRA'])})
        sys.exit(0 if all(x[1] == 0 for x in r) else 1)
    if len(a) < 5: sys.exit(__doc__)
    wd = a[5] if len(a) > 5 else os.path.expanduser('~/c4x-judge1/single')
    (c, code, why), = judge_batch([load_case(*a[:5])], wd)
    print(open(os.path.join(wd, c['name'] + '.verdict.txt')).read().rstrip().rsplit('\n', 1)[0] if code < 3 and os.path.exists(os.path.join(wd, c['name'] + '.verdict.txt')) else '')
    print('JUDGE PASS (%s)' % why if code == 0 else 'JUDGE FAIL %s' % why if code == 1 else 'JUDGE NOORACLE %s' % why if code == 2 else 'JUDGE INFRA %s' % why)
    sys.exit(code)
