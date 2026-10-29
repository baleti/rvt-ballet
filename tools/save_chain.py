"""Repeated save cycles: generation k = open generation k-1, apply one string edit (a new MaterialElem each time), SAVE AS generation k.
Checks per generation: verify 0 undeclared diffs, size stable (+- the edit), element dump of ALL earlier edits still present (no drift), file reopens.
usage: tools/save_chain.py SRC.rvt GENERATIONS OUT.json"""
import os, sys, tempfile, json, time, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
sys.path.insert(0, edit.WL); import wlrec
MATS = [24, 25, 26, 27, 30, 568, 569, 570, 571, 572]
def main(src, n, out):
    cur = src; rows = []; size0 = os.path.getsize(src)
    for g in range(1, n + 1):
        t0 = time.time(); ss = save.SaveSessions(); ss.doc('m', cur)
        eid = MATS[(g - 1) % len(MATS)]; val = 'gen%d-%s' % (g, 'é' * (g % 3))
        try: save.add_edit(ss, 'm', cur, {'op': 'set_string', 'eid': eid, 'value': val, 'match': None if g > len(MATS) else ''})
        except edit.EditError as e: rows.append({'gen': g, 'result': 'EDIT_REFUSED', 'error': str(e)[:120]}); break
        nxt = os.path.join(_T, 'g%d.rvt' % g)
        try: r = save.save_as(ss, 'm', cur, nxt)
        except Exception as e: rows.append({'gen': g, 'result': 'SAVE_FAIL ' + type(e).__name__, 'error': str(e)[:160]}); break
        ss.close()
        m = wlrec.Model(nxt); seen = {}
        for e_ in MATS[:min(g, len(MATS))]:
            try: seen[e_] = [l[4] for l in list(m.find(e_))[0][3] if l[1] == 'ParamValueAString.m_value']
            except Exception: seen[e_] = None
        rows.append({'gen': g, 'size': os.path.getsize(nxt), 'size_delta_vs_gen0': os.path.getsize(nxt) - size0, 'verify_diffs': r['verify']['n_unexpected'], 'edited_value_present': any(isinstance(v, str) and v.startswith('gen%d-' % g) for v in seen[eid] or []),
                     'earlier_edits_present': all(any(isinstance(v, str) and v.startswith('gen%d-' % k) for v in seen[MATS[(k - 1) % len(MATS)]] or []) for k in range(max(1, g - len(MATS) + 1), g)) if g > 1 else True, 'seconds': round(time.time() - t0, 1), 'result': 'OK'})
        print(rows[-1], flush=True)
        if cur != src: os.remove(cur)
        cur = nxt
    ok = sum(r['result'] == 'OK' and r['verify_diffs'] == 0 and r['edited_value_present'] and r['earlier_edits_present'] for r in rows)
    json.dump({'generations': n, 'ok': ok, 'rows': rows}, open(out, 'w'), indent=1); print('CHAIN', n, 'ok', ok, 'sizes', sorted({r.get('size') for r in rows}))
main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
