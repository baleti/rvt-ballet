#!/usr/bin/env python3
"""RESEARCH ONLY: rvtsave_oracle.py with the savegate year gate widened to 2025 in-process (nothing on disk changed; production still refuses 2025). usage: rvtsave_oracle_2025.py SRC 2025 SCENARIO [EID]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from rvtballet import save
save._import()
from savegate import adapters
adapters.RVT_WRITABLE = tuple(adapters.RVT_WRITABLE) + ('2025',)
sys.argv[0] = os.path.join(HERE, 'rvtsave_oracle.py')
import runpy; runpy.run_path(sys.argv[0], run_name='__main__')
