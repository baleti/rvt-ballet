#!/usr/bin/env python3
"""rvtwrite3_noedit.py YEAR OUT.json FILE...: RESEARCH ONLY. Widens savegate RVT_WRITABLE to YEAR in this process, then runs tools/save_real_noedit.py
(no-edit SAVE AS, output must be byte-identical). Shipped gate unchanged; aggregate output only."""
import sys, os, runpy
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
year = sys.argv.pop(1); adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (year,)
if os.environ.get('RVT_LEGACY_LAYOUT'): adapters._first_member_record_sizes = lambda s: {16}   # research only: bypass pre-2024 layout refusal
adapters.RVT_MEMBER_MAX = int(os.environ.get('RVT_MEMBER_MAX', '300000'))
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'save_real_noedit.py'), run_name='__main__')
