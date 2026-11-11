"""c6x-rvtmatrix: set_string with CJK, accents, CRLF/quotes and a 4096-char CJK value on the Autodesk Construction template of EVERY available year (2017..2026): exact readback of the edited Comments, every other element's params identical. YEARS env narrows (comma list). Prints one line per year/case."""
import os, sys, glob, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
CASES = {'cjk': '日本語テスト 漢字', 'mixed': 'Ünï "q" \r\n<&>', 'cjk4096': '界' * 4096}
years = [y for y in (os.environ.get('YEARS') or '2017,2018,2019,2020,2021,2022,2023,2024,2025,2026').split(',')]
done = 0
for y in years:
    fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/%s/*Construction-DefaultMetric.rte' % y)))
    if not fs: print(y, 'no template'); continue
    S = fs[0]; buf = open(S, 'rb').read(); P0 = rvt_params.params(S)
    E = next((e for e, d in P0.items() if g(d).get('Comments') == ''), None)
    if E is None: print(y, 'no empty Comments element'); continue
    for name, val in CASES.items():
        try: out, _ = edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': val})])
        except edit.EditError as e: print(y, name, 'refused:', str(e)[:70]); continue
        d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(out); P1 = rvt_params.params(p)
        bad = [e for e in P0 if e != E and (e not in P1 or g(P0[e]) != g(P1[e]))]
        ok = g(P1[E]).get('Comments') == val and not bad
        print(y, name, 'EXACT, 0 other changed' if ok else 'FAIL (other changed %d)' % len(bad)); assert ok, (y, name, bad[:3]); done += 1
print('OK', done, 'cases')
