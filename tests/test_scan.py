"""fastquery.scan (rvt-ballet sheets|views|levels|grids|counts|elements), which replaced the old fastinfo.scan on 2026-11-14:
(1) Autodesk sample (rst_basic_sample_project, 2020): counts/levels/grids/sheets/views == rvt_entities.parse (the full parser), level elevations decoded;
(2) the counts CLI agrees; (3) the size guard of convert/open points at the query commands. Old/new parity on 42 samples 2020-2026: docs/agent-queries.md.
Skipped when the sample is absent. Run: python -m pytest tests/test_scan.py"""
import os, sys, subprocess, json
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
import pytest
from rvtballet import fastquery as Q, rvtfile as RF

F = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
need = pytest.mark.skipif(not os.path.exists(F), reason='sample absent')


def _agree(rc, pc):
    """header categories agree with the full parser; the scan additionally resolves Family/symbol/surrogate/GStyle/CategoryElem (Revit API: none),
    maps positive-id user subcategories to their parent built-in and labels the rest "(no category...)": named built-ins never drop, totals are equal"""
    names = {v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(Q.__file__)), 'data', 'category_names.json'))).items() if int(k) < 0}
    low = {k: (v, rc.get(k, 0)) for k, v in pc.items() if k in names and rc.get(k, 0) < v}
    assert not low, 'category counts below the full parser: %s' % low
    assert sum(rc.values()) == sum(pc.values()), 'element totals differ'


@need
def test_scan_equals_full_parser():
    RF._paths(); import rvt_entities as E
    r = Q.scan(F, workers=3); p = E.parse(F)
    _agree(r['counts'], p['counts'])
    assert sorted(l['name'] for l in r['levels']) == sorted(l['name'] for l in p['levels'])
    assert all(l['elevation_ft'] is not None for l in r['levels'])
    assert r['grids'] == p['grids']
    assert [(s['number'], s['name'], s['views']) for s in r['sheets']] == [(s['number'], s['name'], s['views']) for s in p['sheets']]
    assert [(v['class'], v['name']) for v in r['views']] == [(v['class'], v['name']) for v in p['views']]
    assert Q.scan(F, counts=False, workers=3)['sheets'] == r['sheets'] == Q.sheets(F, workers=3)
    i = RF.file_info(F); assert i['info'].get('Format') == '2020' and i['partitions'] >= 1


@need
def test_counts_cli_and_size_guard():
    rb = os.path.join(HERE, 'bin', 'rvt-ballet'); RF._paths(); import rvt_entities as E
    out = subprocess.run([rb, 'counts', F, '--json'], capture_output=True, text=True, env=dict(os.environ, RVT_Q_WORKERS='3')); assert out.returncode == 0, out.stderr
    _agree(json.loads(out.stdout)['by_category'], E.parse(F)['counts'])
    g = subprocess.run([rb, 'convert', F, '/nonexistent/out'], capture_output=True, text=True, env=dict(os.environ, RVT_BIG_MB='1')); assert g.returncode == 3 and 'rvt-ballet info' in g.stderr, g.stderr


def test_fastinfo_shim_still_imports():
    from rvtballet import fastinfo
    assert fastinfo.scan and fastinfo.file_info is RF.file_info and fastinfo._sc(2 ** 64 - 1, 8) == -1
