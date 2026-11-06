#!/usr/bin/env python3
"""rvt_diff.py BEFORE.rvt AFTER.rvt [--max N] [--json OUT] [--fields]  record-level diff of two .rvt files (Autodesk samples / synthetic only).
Prints: (1) compound-file streams changed (size old/new, raw-identical?), (2) Global/* streams: decompressed byte-run diffs,
(3) per partition: element headers/records added / removed / changed (by element id, bytes, md5), (4) for changed records the FIELD-level diff
(field name, offset in record, old, new) from the schema decoder (the same one the editor uses).  Offline only; no VM needed.
The VM-driven wrapper that makes the AFTER file with the real Revit API is tools/rvt_diff_vm.py (see ~/demo-state/RVT-DIFF-TOOL.md)."""
import os, sys, json, hashlib, struct, zlib, argparse
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'):
    sys.path.insert(0, os.path.expanduser(p))
import cfb, rvtw, wledit, recwalk, adiff

H12 = lambda b: hashlib.md5(bytes(b)).hexdigest()[:12]


def stream_diff(fa, fb):
    ca, cb = cfb.CFB(open(fa, 'rb').read()).streams(), cfb.CFB(open(fb, 'rb').read()).streams()
    rows = []
    for n in sorted(set(ca) | set(cb)):
        a, b = ca.get(n), cb.get(n)
        if a is None or b is None: rows.append({'stream': n, 'status': 'added' if a is None else 'removed', 'size': (b or a).size}); continue
        same = bytes(a.data) == bytes(b.data)
        if not same: rows.append({'stream': n, 'status': 'changed', 'size_old': a.size, 'size_new': b.size})
    return rows, len(set(ca) | set(cb))


def global_diff(fa, fb, names, maxruns=12):
    out = {}
    for n in names:
        if not n.startswith('Global/') and n not in ('BasicFileInfo', 'Formats/Latest', 'Contents'):
            continue
        try: a, b = adiff.graw(fa, n), adiff.graw(fb, n)
        except Exception as e: out[n] = {'error': str(e)[:80]}; continue
        runs = adiff.ops(a, b, maxda=3000, maxdb=20000)
        out[n] = {'len_old': len(a), 'len_new': len(b), 'runs': [
            {'old_off': i0, 'old_len': (i1 - i0) if i1 else None, 'new_off': j0, 'new_len': (j1 - j0) if j1 else None,
             'old': (a[i0:i1] if i1 else a[i0:i0 + 24]).hex()[:80], 'new': (b[j0:j1] if j1 else b[j0:j0 + 24]).hex()[:80]} for i0, i1, j0, j1 in runs[:maxruns]], 'n_runs': len(runs)}
    return out


def field_log(model, eid):
    """list of (occurrence-keyed field name, value, start, end) of the first decodable record of eid"""
    res = []
    for pn, i, r, log, q in model.find(eid):
        seen = {}
        for l in log:
            k = l[1]; seen[k] = seen.get(k, 0) + 1
            res.append((f'{k}#{seen[k]}', l[4] if len(l) > 4 else None, l[2] - i, l[3] - i))
        return pn, q - i, res
    return None, 0, []


def fmt(v):
    if isinstance(v, float): return round(v, 9)
    if isinstance(v, (bytes, bytearray)): return bytes(v).hex()[:40]
    return v if isinstance(v, (int, str, type(None))) else str(v)[:60]


def diff(fa, fb, want_fields=True, maxrec=200):
    sd, nstreams = stream_diff(fa, fb)
    gd = global_diff(fa, fb, [r['stream'] for r in sd if r['status'] == 'changed'])
    wa, sa = recwalk.walk(fa); wb, sb = recwalk.walk(fb)
    BIG = 1 << 48        # ids above this are walker artifacts (tail item / sentinel bytes read as an id), reported apart
    art = sorted(i for i in set(wa) ^ set(wb) if i >= BIG) + sorted(i for i in set(wa) & set(wb) if i >= BIG and wa[i] != wb[i])
    wa = {k: v for k, v in wa.items() if k < BIG}; wb = {k: v for k, v in wb.items() if k < BIG}
    added = sorted(set(wb) - set(wa)); removed = sorted(set(wa) - set(wb))
    changed = sorted(i for i in set(wa) & set(wb) if wa[i] != wb[i])
    rep = {'streams_total': nstreams, 'streams_changed': sd, 'globals': gd, 'walk_stats_old': {k: list(v) for k, v in sa.items()}, 'walk_stats_new': {k: list(v) for k, v in sb.items()},
           'elements_old': len(wa), 'elements_new': len(wb), 'added': added[:maxrec], 'n_added': len(added), 'removed': removed[:maxrec], 'n_removed': len(removed), 'n_changed': len(changed), 'walker_artifacts': art[:10], 'changed': []}
    if want_fields:
        ma, mb = wledit.Editor(fa).m, wledit.Editor(fb).m
    for eid in changed[:maxrec]:
        row = {'id': eid, 'header_changed': wa[eid]['h'] != wb[eid]['h'], 'rec_len': [[x[0] for x in wa[eid]['r']], [x[0] for x in wb[eid]['r']]]}
        if want_fields:
            try:
                pa, la, fa_ = field_log(ma, eid); pb, lb, fb_ = field_log(mb, eid)
                da, db = {k: v for k, v, s, e in fa_}, {k: v for k, v, s, e in fb_}; off = {k: s for k, v, s, e in fa_}
                row['class_len'] = [la, lb]
                row['fields'] = [{'field': k, 'off': off.get(k), 'old': fmt(da.get(k)), 'new': fmt(db.get(k))} for k in list(dict.fromkeys(list(da) + list(db))) if da.get(k) != db.get(k)][:40]
            except Exception as e: row['field_error'] = str(e)[:100]
        rep['changed'].append(row)
    return rep


def pretty(rep):
    L = [f"streams: {rep['streams_total']} total, {len(rep['streams_changed'])} changed"]
    for r in rep['streams_changed']: L.append(f"  {r['stream']}: {r['status']} {r.get('size_old','')}->{r.get('size_new', r.get('size',''))}")
    for n, g in rep['globals'].items():
        L.append(f"global {n}: len {g.get('len_old')}->{g.get('len_new')} runs {g.get('n_runs')}")
        for r in g.get('runs', [])[:8]: L.append(f"    @{r['old_off']} {r['old_len']}B {r['old']} => {r['new_len']}B {r['new']}")
    L.append(f"elements: {rep['elements_old']} -> {rep['elements_new']}  added {rep['n_added']} {rep['added'][:10]}  removed {rep['n_removed']} {rep['removed'][:10]}  changed {rep['n_changed']}  (walker artifacts ignored: {len(rep['walker_artifacts'])})")
    for c in rep['changed']:
        L.append(f"  id {c['id']} hdr_changed={c['header_changed']} reclen {c['rec_len']}")
        for f in c.get('fields', []): L.append(f"      {f['field']} @{f['off']}: {f['old']} => {f['new']}")
        if c.get('field_error'): L.append('      field decode error: ' + c['field_error'])
    return '\n'.join(L)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('before'); ap.add_argument('after'); ap.add_argument('--max', type=int, default=200)
    ap.add_argument('--json'); ap.add_argument('--nofields', action='store_true'); a = ap.parse_args()
    rep = diff(a.before, a.after, not a.nofields, a.max)
    if a.json: json.dump(rep, open(a.json, 'w'), indent=1, default=str)
    print(pretty(rep))
