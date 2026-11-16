#!/usr/bin/env python3
"""Facades 2024: Revit auto-joined neighbour 802687 when wall 802680 moved +1 ft (witness wmp802680); tool must name it."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from rvt_wall_touch import neighbours
F = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
if not os.path.exists(F): print('SKIP no corpus'); sys.exit(0)
n = neighbours(F, 802680, (1, 0, 0)); assert 802687 in n, n
assert 802687 not in neighbours(F, 802680, (0, 0, 0), 0.25), 'gap 1.33 ft must not touch at rest'
print('PASS', n)
