"""convert a set of corpus files, print a coverage/agreement table (markdown)"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import cli
C = os.path.expanduser('~/rvt-research/corpus')
files = sys.argv[1:] or ['2020/18_rst_basic_sample_project', '2020/20_Residential_Sample_Project', '2020/21_rst_advanced_sample_project', '2020/23_rme_advanced_sample_project',
                         '2024/42_Snowdon_Towers_Sample_HVAC', '2024/43_Snowdon_Towers_Sample_Structural', '2026/54_Snowdon_Towers_Sample_HVAC', '2026/55_Snowdon_Towers_Sample_Structural',
                         '2026/57_Snowdon_Towers_Sample_Plumbing', '2026/58_Snowdon_Towers_Sample_Facades', '2026/59_Snowdon_Towers_Sample_Site']
print('| file | elements | drawn | solid | param | approx | bbox | line | tris | build s |'); print('|---|---|---|---|---|---|---|---|---|---|')
for f in files:
    p = '%s/%s.rvt' % (C, f)
    d = cli.ensure(p, True, log=lambda *a: None)
    m = json.load(open(d + '/meta.json')); tot = {}
    for v in m['coverage'].values():
        for k, n in v.items(): tot[k] = tot.get(k, 0) + n
    drawn = sum(v for k, v in tot.items() if k != 'none')
    print('| %s | %d | %d | %d | %d | %d | %d | %d | %d | %s |' % (f, len(m['elements']), drawn, tot.get('solid', 0), tot.get('param', 0), tot.get('approx', 0), tot.get('bbox', 0), tot.get('line', 0), sum(b['tris'] for b in m['batches']), m['buildSecs']), flush=True)
