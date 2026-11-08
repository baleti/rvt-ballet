"""item 49: chained in-place SAVE!s in one server process must not grow RSS per save (was ~200 MB per save on a 5 MB Autodesk 2026 .rte, until the memory guard refused with 507).
Runs tools/rvtsave_inplace_chain.py (6 saves, Mark edits, private copy); bound: RSS after save 6 within 150 MB of RSS after save 2. Fails without save._gc_after."""
import os, re, subprocess, sys, ast
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.environ.get('RSS_CHAIN_FILE', os.path.expanduser('~/rvt-research/rosetta/2026_grid_level_base.rte'))

def test_rss_flat_over_chained_saves():
    if not os.path.exists(F): print('SKIP no sample'); return
    r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'rvtsave_inplace_chain.py'), F, '6'], capture_output=True, text=True, timeout=900, env=dict(os.environ, CH_IDX='1'))
    rows = [ast.literal_eval(l) for l in r.stdout.splitlines() if l.startswith("{'k'")]
    assert len(rows) == 6 and all(x['status'] == 200 for x in rows), r.stdout[-800:] + r.stderr[-400:]
    grow = rows[5]['rss_mb'] - rows[1]['rss_mb']
    print('rss after save 2 / 6:', rows[1]['rss_mb'], rows[5]['rss_mb'], 'growth', grow)
    assert grow < 150, 'rss grew %d MB over saves 3-6' % grow

if __name__ == '__main__':
    test_rss_flat_over_chained_saves(); print('OK')
