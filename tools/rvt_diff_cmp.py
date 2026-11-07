#!/usr/bin/env python3
"""rvt_diff_cmp.py API_DIFF.json WRITER_DIFF.json   compare a Revit-API-made edit pattern (BASE_AFTER.json from rvt_diff_vm) with the writer's (rvt_diff --json ORIG WRITERFILE).
Prints per element id the fields changed by only one side, fields with different new values (tolerance 1e-9), streams/tables changed by only one side, element add/remove set differences.
Revit's own rewrite noise is excluded by using BASE->AFTER for the API side."""
import sys, json
def load(p): return json.load(open(p))
def fl(rep): return {c['id']: {f['field']: f['new'] for f in c.get('fields', [])} for c in rep['changed']}
def close(a, b):
    if isinstance(a, list) and isinstance(b, list): return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return abs(a - b) < 1e-9
    return a == b
def main():
    A, W = load(sys.argv[1]), load(sys.argv[2]); out = []
    sa = {r['stream'] for r in A['streams_changed']}; sw = {r['stream'] for r in W['streams_changed']}
    out += [f'stream only API: {s}' for s in sorted(sa - sw)] + [f'stream only writer: {s}' for s in sorted(sw - sa)]
    for k in ('added', 'removed'):
        if A['n_' + k] != W['n_' + k]: out.append(f'{k}: API {A["n_"+k]} vs writer {W["n_"+k]}')
    fa, fw = fl(A), fl(W)
    for i in sorted(set(fa) | set(fw)):
        a, w = fa.get(i, {}), fw.get(i, {})
        for f in sorted(set(a) | set(w)):
            if f not in a: out.append(f'id {i} {f}: only writer changes it (-> {w[f]})')
            elif f not in w: out.append(f'id {i} {f}: only API changes it (-> {a[f]})')
            elif not close(a[f], w[f]): out.append(f'id {i} {f}: API {a[f]} vs writer {w[f]}')
    print('\n'.join(out) if out else 'EQUIVALENT at stream/element/field level'); return 1 if out else 0
if __name__ == '__main__': sys.exit(main())
