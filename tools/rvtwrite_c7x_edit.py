#!/usr/bin/env python3
"""rvtwrite_c7x_edit.py YEAR OUT.json FILE...: RESEARCH ONLY. Widens savegate RVT_WRITABLE to YEAR in this process, then runs tools/save_real_edit.py
(one Comments edit + SAVE AS + read-back). The shipped gate is unchanged. Set RVT_KEEP_DIR to keep outputs for VM opens (local only)."""
import sys, os, runpy
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (sys.argv[1],)
sys.argv = [os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get('C7X_TOOL', 'save_real_edit.py'))] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name='__main__')
